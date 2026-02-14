# C Shim and Ada Binding Generation — Extended Reference

Core C shim pattern, h2ads workflow, and type mapping are in SKILL.md. This file has additional details.

## C Shim Implementation Example

```cpp
FooAlgorithm* FooAlgorithm_create(void) {
    return reinterpret_cast<FooAlgorithm*>(new ::FooAlgorithm());
}
void FooAlgorithm_destroy(FooAlgorithm* self) {
    delete reinterpret_cast<::FooAlgorithm*>(self);
}
```

## h2ads Type Visibility Transformations

```ada
-- Make opaque handle private
type Foo_Algorithm is limited private;
type Foo_Algorithm_Access is access all Foo_Algorithm;
private
   type Foo_Algorithm is null record;
```

## YAML Record from C Struct

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
