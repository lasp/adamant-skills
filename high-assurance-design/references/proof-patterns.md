# Proof Patterns

Patterns for structuring formal verification in SPARK Ada (applicable concepts transfer to other verification tools).

## Ghost Lemma Pattern

**Problem**: The prover cannot deduce f(A) = f(B) when A = B for non-expression functions. This blocks proof chaining where validation checks on input must carry through to postconditions on output.

**Solution**:

1. Define shared predicates used by both validation and query functions
2. Write query functions as expression functions (single-line, fully expanded during proof)
3. Create a ghost lemma that proves predicate equality for equal inputs
4. Confine `pragma Assume` to the ghost lemma only

```ada
-- Shared predicate (used by both validation and queries)
function Has_Valid_Scheme (S : String) return Boolean is
  ((S'Length >= 8 and then S (S'First .. S'First + 7) = "https://")
   or else
   (S'Length >= 7 and then S (S'First .. S'First + 6) = "http://"));

-- Query function: expression function calling shared predicate
function Is_HTTP_Or_HTTPS (URL : Valid_URL) return Boolean is
  (Has_Valid_Scheme (To_String (URL)));

-- Constructor with content postcondition (the critical bridge)
function Make_Valid_URL (S : String) return Valid_URL
with Post => To_String (Make_Valid_URL'Result) = S;

-- Ghost lemma: confined assumes for non-expression functions
procedure Lemma_Predicate_Substitution (A, B : String)
with
  Ghost,
  Pre  => A = B and then ...,
  Post => Has_Valid_Scheme (A) = Has_Valid_Scheme (B) and then
          Has_Credentials (A) = Has_Credentials (B) and then
          Has_Private_Host (A) = Has_Private_Host (B)
is
begin
   -- Expression functions prove automatically
   -- Non-expression functions need assumes for pure determinism
   pragma Assume (Has_Credentials (A) = Has_Credentials (B),
     "Pure function determinism: A = B implies f(A) = f(B)");
   pragma Assume (Has_Private_Host (A) = Has_Private_Host (B),
     "Pure function determinism: A = B implies f(A) = f(B)");
end Lemma_Predicate_Substitution;
```

**Proof chain**:
1. Canonicalize validates: `Has_Valid_Scheme(Input) = True`
2. Make_Valid_URL guarantees: `To_String(Result) = Input`
3. Lemma bridges: `predicate(To_String(Result)) = predicate(Input)`
4. Query functions expand: `Is_HTTP_Or_HTTPS(Result) = Has_Valid_Scheme(To_String(Result))`
5. By substitution: postcondition satisfied. QED.

**Result**: 0 assumes in business logic. All assumes confined to one auditable ghost procedure.

## Expression Function Strategy

Prefer expression functions for any function the prover needs to reason about:

- Expression functions are fully expanded during proof (transparent)
- Multi-line body functions require the prover to reason indirectly
- Use expression functions for query/accessor functions on proven types

**Trade-off**: Expression functions cannot contain loops or complex logic. For functions that need loops, accept that they will require either assumes or recursive expression functions with termination proofs.

## Opaque Types as Proof-Driven Encapsulation

Declare validated types as private:

```ada
type Valid_URL is private;
type Short_Code is private;
```

Construction only through proven functions. Code that receives a Valid_URL knows by construction that all validation checks passed. The type system becomes an architectural boundary.

## SPARK RM Constraints to Know

- **7.3.2(2)**: Type_Invariant prohibited on private types in SPARK. Workaround: ghost lemma pattern above.
- Non-expression functions with loops cannot be automatically substituted by the prover.
- `pragma SPARK_Mode (Off)` for FFI marshaling code -- explicitly outside verification boundary.

## FFI Verification Boundary

What to verify vs. what to test:

```
Verified (SPARK):     Core logic, validation, encoding
                      All preconditions and postconditions proven
Tested (property):    FFI marshaling, service layer, integration
                      Hedgehog generators for edge cases
Trusted:              SQLite, crypto library (SPARKNaCl), OS
```

Document the boundary explicitly. Every component should be in exactly one category.
