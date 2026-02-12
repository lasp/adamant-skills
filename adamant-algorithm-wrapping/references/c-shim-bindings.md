# C Shim and Ada Binding Generation

## Stage 1: C Shim Creation

### File Structure
- `<algorithm>Algorithm_c.h` - C shim header (MUST be pure C, no C++ keywords)
- `<algorithm>Algorithm_c.cpp` - C shim implementation
- `<algorithm>Types.h` - Shared types header (DRY: both C++ and C shim include this)

### Opaque Handle Pattern
```c
typedef struct FooAlgorithm FooAlgorithm;
FooAlgorithm* FooAlgorithm_create(void);
void FooAlgorithm_destroy(FooAlgorithm* self);
OutputPayload FooAlgorithm_update(FooAlgorithm* self, const InputPayload* input);
```

### POD Conversion (Eigen types)
```c
typedef struct { float data[3]; } Vector3f_c;
```

### Constant Validation
Export getters for `#define` constants (never `static inline`):
```c
uint32_t FooAlgorithm_getMaxCount(void);
```

### Implementation
```cpp
FooAlgorithm* FooAlgorithm_create(void) {
    return reinterpret_cast<FooAlgorithm*>(new ::FooAlgorithm());
}
void FooAlgorithm_destroy(FooAlgorithm* self) {
    delete reinterpret_cast<::FooAlgorithm*>(self);
}
```

## Stage 2: Ada Bindings (h2ads)

### Command
```bash
h2ads --compiler gcc \
  -I ~/fp32-fsw-xmera/algorithms \
  -b ~/fp32-fsw-xmera/algorithms/<name> \
  ~/fp32-fsw-xmera/algorithms/<name>/<name>Algorithm_c.h
```

### Transformation Rules

**Package rename:** `Foo_Algorithm_C_H` -> `Foo_Algorithm_C`

**Type visibility:**
```ada
-- Make opaque handle private
type Foo_Algorithm is limited private;
type Foo_Algorithm_Access is access all Foo_Algorithm;
private
   type Foo_Algorithm is null record;
```

**Function rename:** `Foo_Algorithm_Create` -> `Create`

**Payload types:** Replace h2ads-generated struct types with Adamant packed record `.C.U_C` types:
```ada
with Nav_Att.C;  -- Instead of Nav_Att_Msg_F32_Payload_H
-- Use Nav_Att.C.U_C in signatures
```

### Constant Validation in Ada
```ada
NUM_SLEWS : constant := 3;
function Get_Num_Slews return Unsigned_32
  with Import => True, Convention => C, External_Name => "FooAlgorithm_getNumSlews";
pragma Assert (Unsigned_32 (NUM_SLEWS) = Get_Num_Slews);
```

## Stage 3: C Struct to Packed Record YAML

### Type Mapping
| C Type | Ada Type | Format |
|--------|----------|--------|
| `float` | `Short_Float` | `F32` |
| `double` | `Long_Float` | `F64` |
| `uint32_t` | `Interfaces.Unsigned_32` | `U32` |
| `int32_t` | `Interfaces.Integer_32` | `I32` |
| `float[3]` | `Packed_F32x3.T` | (none) |
| `double[3]` | `Packed_F64x3.T` | (none) |

**Array types do NOT have a `format` field.** Never use `Natural` for C unsigned types.

### Field Names
Pascal_Case with underscores. Single letters uppercase:
- `sigma_BN` -> `Sigma_Bn`
- `omega_BN_B` -> `Omega_Bn_B`
- `timeTag` -> `Time_Tag`

### YAML Template
```yaml
---
#  /* Original C struct as comment */
#  typedef struct { float timeTag; float r_BN_N[3]; } SomeStruct;
fields:
  - name: Time_Tag
    type: Short_Float
    format: F32
    description: "[s] Time tag"
  - name: R_Bn_N
    type: Packed_F32x3.T
    description: "[m] Position vector"
```
