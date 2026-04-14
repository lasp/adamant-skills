<!-- source: adamant-xmera-components (branch-based, no version pin) -->
# C Shim Patterns

## Opaque Handle Pattern (Header)

```c
/* MIT License ... */
#ifndef F32XIMERA_FOOALGORITHM_C_H
#define F32XIMERA_FOOALGORITHM_C_H

#include <stdint.h>
#include "msgPayloadDef/SomePayload.h"

#ifdef __cplusplus
extern "C" {
#endif

/** @brief Opaque handle to the C++ FooAlgorithm instance. */
typedef struct FooAlgorithm FooAlgorithm;

/** @brief Construct a new FooAlgorithm instance.
 *  @return Pointer to a new FooAlgorithm (must be destroyed). */
FooAlgorithm* FooAlgorithm_create(void);

/** @brief Destroy a previously created FooAlgorithm.
 *  @param self Pointer to the instance to destroy. */
void FooAlgorithm_destroy(FooAlgorithm* self);

/** @brief Run the update step.
 *  @param self      Pointer to the instance.
 *  @param inputMsg  Pointer to input message payload.
 *  @return OutputPayload  The computed output message. */
OutputPayload FooAlgorithm_update(FooAlgorithm* self, const InputPayload* inputMsg);

#ifdef __cplusplus
}
#endif

#endif
```

## C Shim Implementation

```cpp
#include "fooAlgorithm_c.h"
#include "fooAlgorithm.h"

FooAlgorithm* FooAlgorithm_create(void) {
    return reinterpret_cast<FooAlgorithm*>(new ::FooAlgorithm());
}

void FooAlgorithm_destroy(FooAlgorithm* self) {
    delete reinterpret_cast<::FooAlgorithm*>(self);
}

OutputPayload FooAlgorithm_update(FooAlgorithm* self, const InputPayload* inputMsg) {
    return reinterpret_cast<::FooAlgorithm*>(self)->update(*inputMsg);
}
```

## POD Conversion for Eigen Types

When C++ uses Eigen types, define POD equivalents in the header:

```c
typedef struct {
    float data[3];
} Vector3f_c;
```

Convert at the boundary in the .cpp:

```cpp
// C to Eigen (setter)
void FooAlgorithm_setVector(FooAlgorithm* self, Vector3f_c vec) {
    Eigen::Vector3f eigenVec;
    eigenVec << vec.data[0], vec.data[1], vec.data[2];
    reinterpret_cast<::FooAlgorithm*>(self)->setVector(eigenVec);
}

// Eigen to C (getter)
Vector3f_c FooAlgorithm_getVector(FooAlgorithm* self) {
    Eigen::Vector3f eigenVec = reinterpret_cast<::FooAlgorithm*>(self)->getVector();
    Vector3f_c out;
    out.data[0] = eigenVec[0];
    out.data[1] = eigenVec[1];
    out.data[2] = eigenVec[2];
    return out;
}
```

## Bounded Array Structs (CRITICAL)

No array types represented as pointers are allowed in the C shim. Array pointer types are ambiguous -- they could be a pointer to a single element or the first element of an unbounded array. Wrap arrays in a sized struct:

```c
// Don't use Vector3f_c*, instead use:
typedef struct {
    Vector3f_c vec[MIMU_COUNT_C];
} Vector3fArray3_c;
```

Pass bounded array structs by pointer for large types, by value for small types:

```c
// Pass-by-pointer (large arrays):
OutputPayload FooAlgorithm_update(FooAlgorithm* self, const Vector3fArray3_c* inputs);

// Pass-by-value (small structs):
OutputPayload FooAlgorithm_update(FooAlgorithm* self, Vector3fArray3_c inputs);
```

On the Ada side, all types at the C boundary use `.C.U_C` record types with `C_Pass_By_Copy`. The calling convention is explicit in the binding:
- **Pass-by-value**: binding uses `.C.U_C` type directly
- **Pass-by-reference**: binding uses `access constant .C.U_C`

**NOTE**: Ada array types with `Convention => C` are always passed by reference, regardless of whether `access` is used. Only record types with `C_Pass_By_Copy` support true pass-by-value. For bounded array structs passed by value, create both an `.array.yaml` (inner array of record elements) and a `.record.yaml` (wrapper for `C_Pass_By_Copy`).

## Shared Types Header

When the C++ algorithm defines structs or constants used in the public API, create a shared header to eliminate duplication:

```c
/* fooTypes.h */
#ifndef F32XIMERA_FOO_TYPES_H
#define F32XIMERA_FOO_TYPES_H

#define MAX_COUNT 10

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    float param1;
    int param2;
} FooProperties;

#ifdef __cplusplus
}
#endif

#endif
```

Include this header in BOTH the C++ algorithm and the C shim:

```cpp
// fooAlgorithm.h
#include "fooTypes.h"
class FooAlgorithm {
    void setProperties(const FooProperties& props);
};
```

```c
// fooAlgorithm_c.h
#include "fooTypes.h"
void FooAlgorithm_setProperties(FooAlgorithm* self, const FooProperties* props);
```

The shim implementation uses direct passthrough (no field-by-field copying):

```cpp
void FooAlgorithm_setProperties(FooAlgorithm* self, const FooProperties* props) {
    reinterpret_cast<::FooAlgorithm*>(self)->setProperties(*props);
}
```

### When to create shared types

- C++ algorithm defines structs used in public methods
- `#define` constants referenced from Ada
- Custom types passed to or returned from algorithm methods

### When NOT to create shared types

- Internal implementation details
- Types already in `msgPayloadDef/`
- Eigen types (use Vector3f_c POD conversion instead)

## Constant Validation Getters

For `#define` constants that must match Ada constants, export getter functions:

```c
// Header
#define MAX_FOO_COUNT 10
uint32_t FooAlgorithm_getMaxFooCount(void);

// Implementation
uint32_t FooAlgorithm_getMaxFooCount(void) {
    return MAX_FOO_COUNT;
}
```

This enables Ada `pragma Assert` validation at elaboration time.

## Naming Conventions

- **C function names**: `ClassName_methodName` (PascalCase class, camelCase method)
- **Opaque type**: Same name as C++ class
- **File names**: `fooAlgorithm_c.h` / `fooAlgorithm_c.cpp`
- **Header guard**: `F32XIMERA_FOOALGORITHM_C_H`
- Use `reinterpret_cast` (not `static_cast` or C-style casts)
- Use `new`/`delete` (not `malloc`/`free`)
- Input-only parameters: `const Type*`
- Do NOT catch C++ exceptions in shim layer

## Algorithm Patterns

### Stateless (no reset, no config)
```c
AlgorithmName* AlgorithmName_create(void);
void AlgorithmName_destroy(AlgorithmName* self);
OutputPayload AlgorithmName_update(AlgorithmName* self, const InputPayload* input);
```

### Stateful (with reset)
```c
AlgorithmName* AlgorithmName_create(void);
void AlgorithmName_destroy(AlgorithmName* self);
void AlgorithmName_reset(AlgorithmName* self, uint64_t callTime);
OutputPayload AlgorithmName_update(AlgorithmName* self, uint64_t callTime, const InputPayload* input);
```

### Configurable (with getters/setters)
```c
AlgorithmName* AlgorithmName_create(void);
void AlgorithmName_destroy(AlgorithmName* self);
void AlgorithmName_setParameter(AlgorithmName* self, Type value);
Type AlgorithmName_getParameter(const AlgorithmName* self);
OutputPayload AlgorithmName_update(AlgorithmName* self, const InputPayload* input);
```

## Real Examples

### sunSearch (shared types pattern)
- `fp32-fsw-xmera/algorithms/sunSearch/sunSearchTypes.h` -- shared types
- `fp32-fsw-xmera/algorithms/sunSearch/sunSearchAlgorithm_c.h` -- C shim header
- `fp32-fsw-xmera/algorithms/sunSearch/sunSearchAlgorithm_c.cpp` -- C shim impl

### attTrackingError (Eigen conversion pattern)
- `fp32-fsw-xmera/algorithms/attTrackingError/attTrackingErrorAlgorithm_c.h`
- `fp32-fsw-xmera/algorithms/attTrackingError/attTrackingErrorAlgorithm_c.cpp`

### navAggregate (shared output type pattern)
- `fp32-fsw-xmera/algorithms/navAggregate/navAggregateOutput.h` -- shared output type
- `fp32-fsw-xmera/algorithms/navAggregate/navAggregateAlgorithm_c.h`
