<!-- validated: adamant@80c1f5f 2026-02-23 (main) -->
# Advanced Contract Patterns

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
