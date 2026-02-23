<!-- validated: adamant@d9cd178 2026-02-23 (main) -->
# Advanced Contract Patterns

## State Record Return Pattern

When a function transforms multiple related fields (e.g., a tick handler updating both a counter and a mode flag), return a record containing the new state. This lets the postcondition relate all output fields to input fields in a single contract:

```ada
type My_State is record
   Counter : Unsigned_32;
   Active  : Boolean;
end record;

type Tick_Result is record
   New_State     : My_State;
   Action_Needed : Boolean;
end record;

function Evaluate_Tick (State : My_State; Limit : Unsigned_16) return Tick_Result
with
   Global => null,
   Post   =>
      -- Counter always increments (saturating)
      (if State.Counter < Unsigned_32'Last
       then Evaluate_Tick'Result.New_State.Counter = State.Counter + 1
       else Evaluate_Tick'Result.New_State.Counter = Unsigned_32'Last)
      and then
      -- Action only triggers on transition (not already active, at limit)
      (if Evaluate_Tick'Result.Action_Needed then
          not State.Active and then Evaluate_Tick'Result.New_State.Active = True
       else
          Evaluate_Tick'Result.New_State.Active = State.Active);
```

The body uses `or` for conditional flag update: `Active => State.Active or Should_Act`. The prover handles the boolean algebra at level 2.

Key: keep the record fields as simple scalar types (Boolean, Unsigned_N). No access types, no tagged types, no controlled types.

## Proof Chain Walkthrough

This pattern proves security/correctness properties propagate through an opaque type boundary. The prover needs help because it cannot see inside private types.

### Architecture

```
Validate(Input)           -- checks predicates on raw string
  |
  v
Make_Opaque(Input)        -- wraps in private type, Post: Accessor(Result) = Input
  |
  v
Query(Opaque_Value)       -- expression functions calling SAME predicates on Accessor(Value)
  |
  v
Ghost Lemma               -- proves predicate(Accessor(Value)) = predicate(Input)
                          -- when Accessor(Value) = Input
```

### Step 1: Shared Predicates

Define validation logic as functions usable by BOTH the validator and the queries:

```ada
--  Expression function -- prover inlines automatically
function Has_Valid_Scheme (S : String) return Boolean is
   ((S'Length >= 8 and then S (S'First .. S'First + 7) = "https://")
    or else
    (S'Length >= 7 and then S (S'First .. S'First + 6) = "http://"))
with Pre => S'Length >= 1 and then S'First >= 1;

--  Non-expression function (has a body) -- prover cannot inline
function Has_Credentials (S : String) return Boolean
with Pre => S'Length >= 1 and then S'First >= 1;
```

### Step 2: Constructor with Content Postcondition

```ada
function Make_Valid (S : String) return Valid_Type
with
   Pre  => S'Length >= 1 and then S'Length <= Max_Length and then S'First = 1,
   Post => To_String (Make_Valid'Result) = S and then
           Length (Make_Valid'Result) = S'Length;
```

This postcondition is the bridge. It guarantees the accessor returns the original input.

### Step 3: Query Functions as Expression Functions

```ada
function Is_HTTP_Or_HTTPS (V : Valid_Type) return Boolean is
   (Has_Valid_Scheme (To_String (V)))
with Pre => Length (V) >= 7;

function No_Credentials (V : Valid_Type) return Boolean is
   (not Has_Credentials (To_String (V)))
with Pre => Length (V) >= 1;
```

Because these are expression functions calling the shared predicates, the prover can substitute.

### Step 4: Ghost Lemma for Non-Expression Functions

```ada
procedure Lemma_Predicate_Substitution (A : String; B : String)
with
   Ghost,
   Pre  => A = B and then <bounds on A and B>,
   Post => Has_Valid_Scheme (A) = Has_Valid_Scheme (B) and then
           Has_Credentials (A) = Has_Credentials (B)
is
begin
   --  Expression functions: prover handles automatically.
   --  Non-expression functions need confined assumes:
   pragma Assume (Has_Credentials (A) = Has_Credentials (B),
                  "Pure function determinism: A = B implies f(A) = f(B)");
end Lemma_Predicate_Substitution;
```

### Step 5: Main Function Uses the Chain

```ada
function Validate (Input : String) return Result_Type is
   Result : Result_Type;
begin
   --  Each check establishes a predicate fact
   if not Has_Valid_Scheme (Input) then
      return (Status => Invalid_Scheme, ...);
   end if;
   --  Now: Has_Valid_Scheme(Input) = True

   if Has_Credentials (Input) then
      return (Status => Credentials_Present, ...);
   end if;
   --  Now: Has_Credentials(Input) = False

   --  Construct opaque value -- postcondition bridges
   Result.Value := Make_Valid (Input);
   Result.Status := Success;

   --  Apply ghost lemma
   Lemma_Predicate_Substitution (To_String (Result.Value), Input);

   --  These assertions are now provable by substitution:
   pragma Assert (Has_Valid_Scheme (To_String (Result.Value)));
   pragma Assert (not Has_Credentials (To_String (Result.Value)));

   return Result;
   --  Postcondition: Is_HTTP_Or_HTTPS(Result.Value) and No_Credentials(Result.Value)
   --  Proved by: query functions inline to predicate calls on To_String,
   --  lemma proves predicate equality, checked predicates provide the values.
end Validate;
```

## Type Invariant Patterns

### Range-Constrained State Machine

```ada
type State is (Idle, Running, Error, Shutdown);

subtype Active_State is State range Idle .. Error;

procedure Transition (Current : in out State; Event : Event_Type)
with
   Pre  => Current in Active_State,  -- Can't transition from Shutdown
   Post => (if Event = Fatal then Current = Shutdown
            else Current in Active_State);
```

### Counter with Overflow Protection

```ada
type Safe_Counter is range 0 .. 1_000_000;

procedure Increment (C : in out Safe_Counter)
with
   Pre  => C < Safe_Counter'Last,
   Post => C = C'Old + 1;

procedure Add (C : in out Safe_Counter; Amount : Safe_Counter)
with
   Pre  => Safe_Counter'Last - C >= Amount,
   Post => C = C'Old + Amount;
```

### Array Bounded Operations

```ada
type Buffer is array (1 .. 256) of Unsigned_8;
subtype Buffer_Index is Integer range 1 .. 256;
subtype Buffer_Length is Integer range 0 .. 256;

procedure Write_Byte (Buf : in out Buffer; Pos : Buffer_Index; Val : Unsigned_8)
with
   Global  => null,
   Depends => (Buf => (Buf, Pos, Val)),
   Post    => Buf (Pos) = Val and then
              (for all I in Buffer_Index =>
                 (if I /= Pos then Buf (I) = Buf'Old (I)));
```

## Contract Patterns for Adamant Component Logic

### Parameter Validation

```ada
--  In a separate _logic package with SPARK_Mode => On

function Is_Valid_Threshold (Value : Float) return Boolean is
   (Value >= 0.0 and then Value <= 100.0 and then Value'Valid);

function Validate_Config
   (Threshold : Float;
    Timeout   : Natural)
   return Boolean
with
   Global => null,
   Post   => (if Validate_Config'Result then
                 Is_Valid_Threshold (Threshold) and then
                 Timeout <= 3600);
```

### Lookup Table with Bounds Proof

```ada
type Table_Index is range 0 .. 15;
type Lookup_Table is array (Table_Index) of Integer;

function Lookup (T : Lookup_Table; Key : Table_Index) return Integer
with
   Global => null,
   Post   => Lookup'Result = T (Key);
--  Trivial but proves no index-out-of-bounds possible
```

### CRC / Checksum Computation

```ada
type Byte_Array is array (Positive range <>) of Unsigned_8;

function Compute_CRC (Data : Byte_Array) return Unsigned_16
with
   Global => null,
   Pre    => Data'Length >= 1 and then Data'First >= 1,
   Post   => True;  -- Absence of runtime errors is the proof goal
```

For checksums, the primary proof goal is absence of runtime errors (overflow, index bounds), not functional correctness of the algorithm itself.

## Proving Absence of Runtime Errors

This is often the most practical use of SPARK in Adamant -- proving code cannot crash at runtime.

### Strategy

1. Set mode to `silver` or `gold`
2. GNATprove checks every potential runtime error:
   - Integer overflow
   - Array index out of bounds
   - Division by zero
   - Range constraint violations
   - Discriminant check failures
3. Add Pre/Post contracts to make the proofs go through
4. No functional postconditions needed -- just Pre to establish bounds

### Example: Safe Array Copy

```ada
procedure Copy_Region
   (Src  : Byte_Array;
    Dst  : in out Byte_Array;
    From : Positive;
    To   : Positive;
    Len  : Natural)
with
   Pre => Len > 0 and then
          From >= Src'First and then
          From + Len - 1 <= Src'Last and then
          To >= Dst'First and then
          To + Len - 1 <= Dst'Last
is
begin
   for I in 0 .. Len - 1 loop
      Dst (To + I) := Src (From + I);
      pragma Loop_Invariant (I >= 0);
      pragma Loop_Invariant (From + I >= Src'First);
      pragma Loop_Invariant (From + I <= Src'Last);
      pragma Loop_Invariant (To + I >= Dst'First);
      pragma Loop_Invariant (To + I <= Dst'Last);
   end loop;
end Copy_Region;
```

## SPARKNaCl Integration

SPARKNaCl provides formally verified cryptographic primitives. When using in Adamant:

### Type Conversions

SPARKNaCl uses `Byte_Seq` (0-indexed) while Ada strings are 1-indexed:

```ada
--  String to Byte_Seq
Msg_Bytes : Byte_Seq (0 .. N32 (Message'Length) - 1) := (others => 0);

for I in Message'Range loop
   Msg_Bytes (N32 (I - Message'First)) := Byte (Character'Pos (Message (I)));
   pragma Loop_Invariant (I >= Message'First);
end loop;
```

### HMAC Pattern

```ada
with SPARKNaCl;              use SPARKNaCl;
with SPARKNaCl.MAC;          use SPARKNaCl.MAC;
with SPARKNaCl.Hashing.SHA256;

function Compute_HMAC (Message : String; Key : Key_Type) return Digest
with
   Pre  => Message'Length >= 1 and then Message'First = 1,
   Post => Compute_HMAC'Result'Length = 32
is
   Output : SPARKNaCl.Hashing.SHA256.Digest;
begin
   --  Convert, compute, return
   HMAC_SHA_256 (Output, Msg_Bytes, Key_Bytes);
   return Output;
end Compute_HMAC;
```

## Pragma Assume Discipline

### Rules
1. **Zero assumes in business logic** -- all assumes confined to ghost lemmas
2. Each assume has a documented mathematical justification string
3. Assumes are for bridging prover limitations, not papering over real issues
4. Audit: `grep -rn "pragma Assume" *.adb` should show only ghost procedures

### Acceptable Assumes
- Pure function determinism: `A = B implies f(A) = f(B)` for side-effect-free functions
- Mathematical identities the prover's solvers can't handle

### Unacceptable Assumes
- Assuming inputs are in range (use Pre instead)
- Assuming external state hasn't changed (use Global/Depends)
- Anything that could be proven with a stronger invariant or loop invariant

## Bounded Float Subtype Pattern

When proving float arithmetic (subtraction, negation), full-range floats cause overflow. Define bounded subtypes:

```ada
-- Guarantee a - b fits in Short_Float for any a, b in Bounded_Float
subtype Bounded_Float is Short_Float range -1.0E+37 .. 1.0E+37;
subtype Positive_Float is Short_Float range Short_Float'Succ (0.0) .. 1.0E+37;

procedure Step_Toward
  (Current : in Bounded_Float;
   Target  : in Bounded_Float;
   Step    : in Positive_Float;
   Result  : out Bounded_Float)
with Global => null,
     Post =>
       (if Current < Target then
          (if Target - Current <= Step then Result = Target
           else Result = Current + Step)
        elsif Current > Target then
          (if Current - Target <= Step then Result = Target
           else Result = Current - Step)
        else Result = Target);
```

Key: the subtype range (1E37 vs 3.4E38) provides enough headroom that `a - b` and `a + step` stay within Short_Float range without explicit Pre.

## Linear Calibration with Saturation Pattern

Widen to U32 intermediate, saturate back to U16:

```ada
function Calibrate
  (Raw : Unsigned_16; Gain : Unsigned_16; Offset : Unsigned_16) return Unsigned_16
with Global => null,
     Post =>
       (if Unsigned_32 (Raw) * Unsigned_32 (Gain) / 100 + Unsigned_32 (Offset)
           > Unsigned_32 (Unsigned_16'Last)
        then Calibrate'Result = Unsigned_16'Last
        else Calibrate'Result = Unsigned_16 (
               Unsigned_32 (Raw) * Unsigned_32 (Gain) / 100 + Unsigned_32 (Offset)));
```

The prover handles the U32 arithmetic and conversion checks automatically at level 2.

## Sawtooth Wrap Detection via Subtraction

When checking if `Value + Step > Max` with unsigned types, the addition can overflow. Reformulate as a subtraction test:

```ada
function Should_Wrap (Value, Step, Max : Unsigned_16) return Boolean
with
   Global => null,
   Post   => Should_Wrap'Result = (Step > Max or else Value > Max - Step);
```

When `Step > Max`, wrapping always occurs. Otherwise `Max - Step` is safe (no underflow) and `Value > Max - Step` is equivalent to `Value + Step > Max` without overflow risk. The prover handles this at level 2.

Use with a `Next_Value` function:

```ada
function Next_Value (Value, Step, Max : Unsigned_16) return Unsigned_16
with
   Global => null,
   Post   => (if Should_Wrap (Value, Step, Max)
              then Next_Value'Result = 0
              else Next_Value'Result = Value + Step);
```

## Window-Based State Machine Logic

For periodic window logic (watchdog kickers, duty cycle monitors), extract window boundary and action predicates:

```ada
function Window_Complete (Ticks, Window_Size : Unsigned_16) return Boolean
with
   Global => null,
   Post   => Window_Complete'Result = (Ticks >= Window_Size);

function Should_Act (Enabled : Boolean; Ticks, Window_Size : Unsigned_16) return Boolean
with
   Global => null,
   Post   => Should_Act'Result = (Enabled and then Ticks >= Window_Size);

function Missed_Action (Detection_Enabled : Boolean; Acted_This_Window : Boolean) return Boolean
with
   Global => null,
   Post   => Missed_Action'Result = (Detection_Enabled and then not Acted_This_Window);
```

These compose naturally: the component calls `Window_Complete` to check boundaries, `Should_Act` for the action decision, and `Missed_Action` at window end. All prove trivially as the bodies mirror the postconditions.

## Bitfield Extraction with Shift_Right

Extracting sub-words from wider types proves cleanly when the mask is explicit:

```ada
function Low_Word (Status : Unsigned_32) return Unsigned_16
with
   Global => null,
   Post   => Low_Word'Result = Unsigned_16 (Status and 16#FFFF#);

function High_Word (Status : Unsigned_32) return Unsigned_16
with
   Global => null,
   Post   => High_Word'Result = Unsigned_16 (Shift_Right (Status, 16) and 16#FFFF#);
```

The `and 16#FFFF#` mask ensures the conversion to `Unsigned_16` is always in range. The prover verifies this at level 2 without additional hints.

## Modular Decimation Pattern

Forward every Nth item:

```ada
function Should_Forward (Count : Unsigned_32; Factor : Unsigned_16) return Boolean
with Global => null,
     Pre => Factor > 0,
     Post => Should_Forward'Result = (Count mod Unsigned_32 (Factor) = 0);
```

## Type Width Matching for mod-then-convert

When converting `X mod Period` to a narrower type, make Period the same width as the target:

```ada
-- Period : Unsigned_16 guarantees (Tick mod U32(Period)) fits in U16
function Simulated_Voltage
  (Tick : Unsigned_32; Base : Unsigned_16; Period : Unsigned_16) return Unsigned_16
with Pre => Period > 0;
```

## Signed Integer Saturation

For signed offsets/corrections, the postcondition must cover three branches (positive, negative, zero) and both saturation directions:

```ada
procedure Apply_Correction (
   Offset_Ms  : in out Integer_32;
   Correction : in Integer_32
)
with
   Global => null,
   Post   => (if Correction > 0 and then Offset_Ms'Old <= Integer_32'Last - Correction
              then Offset_Ms = Offset_Ms'Old + Correction)
         and then (if Correction < 0 and then Offset_Ms'Old >= Integer_32'First - Correction
                   then Offset_Ms = Offset_Ms'Old + Correction)
         and then (if Correction = 0 then Offset_Ms = Offset_Ms'Old);
```

The implementation checks each branch separately, saturating to `Integer_32'Last` or `Integer_32'First` on overflow. The postcondition only specifies the non-saturating cases -- saturating cases are left as implementation freedom.

## Bitwise Mask Postconditions

The prover can reason about bitwise operations. Two provable patterns:

```ada
-- Apply_Mask: result has no bits outside mask
function Apply_Mask (Value : Unsigned_32; Mask : Unsigned_32) return Unsigned_32 is
   (Value and Mask)
with Post => (Apply_Mask'Result and (not Mask)) = 0;

-- Changed_Bits: XOR is 0 when inputs are equal
function Changed_Bits (A : Unsigned_32; B : Unsigned_32) return Unsigned_32 is
   (A xor B)
with Post => (if A = B then Changed_Bits'Result = 0);
```

Both prove automatically at level 2 as expression functions.

## Bounded Array Index for Circular Buffers

Unconstrained arrays with `Natural range <>` cause proof failures because `Buffer'Length` can overflow `Natural`. Use a bounded index subtype:

```ada
Max_Buffer_Size : constant := 256;
subtype Buffer_Index is Natural range 0 .. Max_Buffer_Size - 1;
type Id_Array is array (Buffer_Index range <>) of Unsigned_16;

procedure Insert (
   Item    : in Unsigned_16;
   Buffer  : in out Id_Array;
   Head    : in Buffer_Index;
   Count   : in Natural;
   New_Head  : out Buffer_Index;
   New_Count : out Natural
)
with
   Global => null,
   Pre    => Buffer'Length > 0
      and then Head in Buffer'Range
      and then Count <= Buffer'Length,
   Post   => New_Head in Buffer'Range
      and then New_Count <= Buffer'Length
      and then Buffer (Head) = Item;
```

The bounded subtype ensures `Buffer'Length` fits in `Natural`, eliminating the overflow class.

## Conditional Conservation with Saturation

When counters saturate, exact arithmetic conservation breaks. Gate conservation on the non-saturation case:

```ada
procedure Record_Result (
   Is_Good      : in Boolean;
   Good_Count   : in Unsigned_32;
   Bad_Count    : in Unsigned_32;
   Total        : in Unsigned_32;
   New_Good     : out Unsigned_32;
   New_Bad      : out Unsigned_32;
   New_Total    : out Unsigned_32
)
with
   Global => null,
   Post   =>
      New_Total >= Total
      and then (if Is_Good then New_Good >= Good_Count and then New_Bad = Bad_Count
                else New_Bad >= Bad_Count and then New_Good = Good_Count)
      -- Conservation holds when no saturation occurs:
      and then (if Good_Count < Unsigned_32'Last and then Bad_Count < Unsigned_32'Last
                   and then Total < Unsigned_32'Last then
                  (New_Good - Good_Count) + (New_Bad - Bad_Count) = New_Total - Total);
```

## Rate Calculation with 64-bit Intermediate

For percentage or permille calculations, use `Unsigned_64` to avoid intermediate overflow:

```ada
function Error_Rate_Permille (Errors : Unsigned_32; Total : Unsigned_32) return Unsigned_32
with
   Global => null,
   Post   => (if Total = 0 then Error_Rate_Permille'Result = 0
              else Error_Rate_Permille'Result <= 1000);

-- Body:
function Error_Rate_Permille (Errors : Unsigned_32; Total : Unsigned_32) return Unsigned_32 is
begin
   if Total = 0 then return 0; end if;
   declare
      N : constant Unsigned_64 := Unsigned_64 (Errors) * 1000;
      R : constant Unsigned_64 := N / Unsigned_64 (Total);
   begin
      if R > 1000 then return 1000; else return Unsigned_32 (R); end if;
   end;
end Error_Rate_Permille;
```

The `<= 1000` postcondition proves cleanly because of the explicit clamp.

## Enum Classification by Threshold

When routing or classifying values into discrete categories based on thresholds, return an enumeration with a complete postcondition:

```ada
type Priority_Level is (High, Normal, Low);

function Classify_Priority (Seq_Count : Unsigned_16; High_Threshold : Unsigned_16; Low_Threshold : Unsigned_16) return Priority_Level
with
   Global => null,
   Post   => (if Seq_Count >= High_Threshold then Classify_Priority'Result = High
              elsif Seq_Count < Low_Threshold then Classify_Priority'Result = Low
              else Classify_Priority'Result = Normal);
```

The postcondition fully specifies the mapping. The body is a direct if/elsif/else chain that mirrors the postcondition. Proves trivially at level 2. Works for any number of thresholds -- just extend the enum and add branches.

## Constrained Subtype for Mux/Router Source Selection

When routing based on a small set of valid source IDs, define a constrained subtype rather than using raw unsigned. The prover reasons about the subtype's range to prove completeness:

```ada
subtype Source_Id is Unsigned_16 range 0 .. 2;
Both_Sources : constant Source_Id := 0;

function Should_Forward (Packet_Source : Source_Id; Active : Source_Id) return Boolean
with Global => null,
     Post => Should_Forward'Result = (Active = Both_Sources or else Active = Packet_Source);
```

The subtype constraint means the prover knows there are only 3 possible values, making exhaustive reasoning tractable at level 2.

## Saturating Addition via U64 Widening

For adding two `Unsigned_32` values without overflow, widen to `Unsigned_64` and clamp:

```ada
function Saturating_Add (A : Unsigned_32; B : Unsigned_32) return Unsigned_32
with
   Global => null,
   Post   => (if Unsigned_64 (A) + Unsigned_64 (B) > Unsigned_64 (Unsigned_32'Last)
              then Saturating_Add'Result = Unsigned_32'Last
              else Saturating_Add'Result = A + B);

-- Body:
function Saturating_Add (A : Unsigned_32; B : Unsigned_32) return Unsigned_32 is
   Sum_64 : constant Unsigned_64 := Unsigned_64 (A) + Unsigned_64 (B);
begin
   if Sum_64 > Unsigned_64 (Unsigned_32'Last) then
      return Unsigned_32'Last;
   else
      return Unsigned_32 (Sum_64);
   end if;
end Saturating_Add;
```

The prover verifies the `Unsigned_32` conversion is safe because the if-check guarantees `Sum_64 <= Unsigned_32'Last`. Generalizes to any width pair (U16 via U32, etc.).

## Linear Search with Postcondition on Unconstrained Arrays

For route table lookup or any linear search returning an index or sentinel, use an unconstrained array type in the logic package and a sentinel constant:

```ada
type Route_Entry is record
   Active    : Boolean;
   Packet_Id : Unsigned_16;
   Channel   : Unsigned_8;
end record;

type Route_Table is array (Natural range <>) of Route_Entry;
No_Route : constant Natural := Natural'Last;

function Lookup (Table : Route_Table; Packet_Id : Unsigned_16) return Natural
with
   Global => null,
   Post   =>
      (if Lookup'Result /= No_Route
       then Lookup'Result in Table'Range
            and then Table (Lookup'Result).Active
            and then Table (Lookup'Result).Packet_Id = Packet_Id);
```

The body is a simple for loop. The prover verifies:
- Return value is always a valid index or the sentinel
- When found, the entry matches the search key and is active
- No array bounds violations in the loop

Key: the postcondition only specifies the "found" case. The "not found" case (returns `No_Route`) is unconstrained -- callers check `Result /= No_Route` before indexing. This avoids needing a universal quantifier (`for all`) which can be expensive at level 2.

Similarly, `Find_Empty_Slot` uses `not Table(Result).Active` in the postcondition.

## Multi-Metric State Determination

When determining a system state from multiple independent metrics, structure the postcondition as a cascade of implications matching the if/elsif chain:

```ada
type System_State is (Idle, Active, Degraded, Emergency);

function Determine_State (
   Error_Count : Unsigned_16;
   Error_Threshold : Unsigned_16;
   Cpu_Load : Unsigned_16;
   Degraded_Cpu_Threshold : Unsigned_16
) return System_State
with
   Global => null,
   Post =>
      (if Error_Count >= Error_Threshold then Determine_State'Result = Emergency)
      and then
      (if Error_Count < Error_Threshold and then Cpu_Load >= Degraded_Cpu_Threshold
       then Determine_State'Result = Degraded);
```

The postcondition specifies the two "deterministic" branches (Emergency, Degraded) but leaves the default (Active) unspecified -- it follows by elimination. This is intentional: specifying only the critical transitions keeps the contract readable and provable. Adding a third clause for Active would work but adds no safety value.

## Completion Percentage with Constant Threshold

When computing progress percentage against a constant, the prover can inline the constant value to verify bounds:

```ada
Completion_Threshold : constant Unsigned_32 := 1_000;

function Completion_Percentage (Pages_Scrubbed : Unsigned_32) return Unsigned_8
with
   Global => null,
   Post   => Completion_Percentage'Result <= 100;
```

Body uses `Unsigned_64` widening: `(Pages_64 * 100) / Threshold_64`, clamped to 100. The constant threshold eliminates the need for a `Pre => Threshold > 0` guard -- the prover knows the divisor is 1000 by inlining the constant. This pattern applies to any fixed-denominator percentage calculation.
