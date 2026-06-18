#include <stdlib.h>
#include <string.h>

#include "function.h"
#include "object.h"
#include "value.h"

typedef struct EnactAttribute {
    char *name;
    EnactValue value;
    struct EnactAttribute *next;
} EnactAttribute;

typedef struct EnactMethod {
    char *name;
    EnactFunction *function;
    struct EnactMethod *next;
} EnactMethod;

typedef struct EnactClassLink {
    EnactClass *class_value;
    struct EnactClassLink *next;
} EnactClassLink;

struct EnactClass {
    size_t ref_count;
    char *name;
    EnactClassLink *superclasses;
    EnactMethod *methods;
};

struct EnactObject {
    size_t ref_count;
    EnactClass *class_value;
    EnactAttribute *attributes;
    EnactCollectionKind collection_kind;
    EnactList *collection_items;
};

typedef struct EnactClassVector {
    EnactClass **items;
    size_t count;
    size_t capacity;
} EnactClassVector;

typedef struct EnactClassSequence {
    const EnactClassVector *classes;
    size_t index;
} EnactClassSequence;

static char *enact_object_copy_text(const char *text)
{
    size_t length;
    char *copy;

    if (!text) {
        text = "";
    }

    length = strlen(text);
    copy = malloc(length + 1);
    if (!copy) {
        return NULL;
    }

    memcpy(copy, text, length + 1);
    return copy;
}

static EnactClassLink *enact_class_link_new(EnactClass *class_value)
{
    EnactClassLink *link;

    if (!class_value) {
        return NULL;
    }

    link = calloc(1, sizeof(*link));
    if (!link) {
        return NULL;
    }

    link->class_value = enact_class_retain(class_value);
    if (!link->class_value) {
        free(link);
        return NULL;
    }

    return link;
}

static int enact_class_link_append(EnactClassLink **head, EnactClass *class_value)
{
    EnactClassLink *link;
    EnactClassLink *tail;

    if (!head) {
        return 0;
    }

    link = enact_class_link_new(class_value);
    if (!link) {
        return 0;
    }

    if (!*head) {
        *head = link;
        return 1;
    }

    tail = *head;
    while (tail->next) {
        tail = tail->next;
    }
    tail->next = link;
    return 1;
}

static void enact_class_link_release_all(EnactClassLink *link)
{
    while (link) {
        EnactClassLink *next = link->next;

        enact_class_release(link->class_value);
        free(link);
        link = next;
    }
}

static EnactClass *enact_class_alloc_named(const char *name)
{
    EnactClass *class_value = calloc(1, sizeof(*class_value));

    if (!class_value) {
        return NULL;
    }

    class_value->name = enact_object_copy_text(name);
    if (!class_value->name) {
        free(class_value);
        return NULL;
    }

    class_value->ref_count = 1;
    return class_value;
}

EnactClass *enact_class_new(const char *name)
{
    return enact_class_alloc_named(name);
}

EnactClass *enact_class_new_with_superclass(const char *name, EnactClass *superclass)
{
    EnactClass *class_value = enact_class_alloc_named(name);

    if (!class_value) {
        return NULL;
    }

    if (superclass) {
        if (!enact_class_link_append(&class_value->superclasses, superclass)) {
            enact_class_release(class_value);
            return NULL;
        }
    }
    return class_value;
}

EnactClass *enact_class_new_with_superclasses(const char *name, EnactList *superclasses)
{
    EnactClass *class_value = enact_class_alloc_named(name);

    if (!class_value) {
        return NULL;
    }

    while (superclasses) {
        const EnactValue *value = enact_list_head(superclasses);

        if (!value || value->kind != ENACT_VALUE_CLASS ||
            !enact_class_link_append(&class_value->superclasses, value->as.as_class)) {
            enact_class_release(class_value);
            return NULL;
        }

        superclasses = enact_list_tail(superclasses);
    }

    return class_value;
}

EnactClass *enact_class_retain(EnactClass *class_value)
{
    if (!class_value) {
        return NULL;
    }

    class_value->ref_count += 1;
    return class_value;
}

static void enact_method_release_all(EnactMethod *method)
{
    while (method) {
        EnactMethod *next = method->next;

        free(method->name);
        enact_function_release(method->function);
        free(method);
        method = next;
    }
}

void enact_class_release(EnactClass *class_value)
{
    if (!class_value) {
        return;
    }

    if (class_value->ref_count > 1) {
        class_value->ref_count -= 1;
        return;
    }

    free(class_value->name);
    enact_method_release_all(class_value->methods);
    enact_class_link_release_all(class_value->superclasses);
    free(class_value);
}

const char *enact_class_name(const EnactClass *class_value)
{
    return class_value ? class_value->name : "";
}

EnactClass *enact_class_superclass(const EnactClass *class_value)
{
    if (!class_value || !class_value->superclasses) {
        return NULL;
    }

    return class_value->superclasses->class_value;
}

static int enact_class_inherits_name(const EnactClass *class_value, const char *name)
{
    const EnactClassLink *link;

    if (!class_value || !name) {
        return 0;
    }
    if (strcmp(enact_class_name(class_value), name) == 0) {
        return 1;
    }

    for (link = class_value->superclasses; link; link = link->next) {
        if (enact_class_inherits_name(link->class_value, name)) {
            return 1;
        }
    }

    return 0;
}

static EnactCollectionKind enact_class_collection_kind(const EnactClass *class_value)
{
    if (enact_class_inherits_name(class_value, "Set")) {
        return ENACT_COLLECTION_SET;
    }
    if (enact_class_inherits_name(class_value, "Bag")) {
        return ENACT_COLLECTION_BAG;
    }

    return ENACT_COLLECTION_NONE;
}

static int enact_class_superclasses_from_link(const EnactClassLink *link, EnactList **out)
{
    EnactList *tail = NULL;
    EnactList *result;
    EnactValue class_value;

    if (!out) {
        return 0;
    }
    if (!link) {
        *out = NULL;
        return 1;
    }

    if (!enact_class_superclasses_from_link(link->next, &tail)) {
        return 0;
    }

    class_value = enact_value_make_class(link->class_value);
    result = enact_list_cons(&class_value, tail);
    enact_list_release(tail);
    if (!result) {
        return 0;
    }

    *out = result;
    return 1;
}

int enact_class_superclasses(const EnactClass *class_value, EnactList **out)
{
    if (!class_value || !out) {
        return 0;
    }

    return enact_class_superclasses_from_link(class_value->superclasses, out);
}

static void enact_class_vector_free(EnactClassVector *vector)
{
    if (!vector) {
        return;
    }

    free(vector->items);
    vector->items = NULL;
    vector->count = 0;
    vector->capacity = 0;
}

static int enact_class_vector_contains(const EnactClassVector *vector, EnactClass *class_value)
{
    size_t index;

    if (!vector || !class_value) {
        return 0;
    }

    for (index = 0; index < vector->count; index += 1) {
        if (vector->items[index] == class_value) {
            return 1;
        }
    }

    return 0;
}

static int enact_class_vector_reserve(EnactClassVector *vector, size_t capacity)
{
    EnactClass **items;
    size_t next_capacity;

    if (!vector) {
        return 0;
    }
    if (capacity <= vector->capacity) {
        return 1;
    }

    next_capacity = vector->capacity ? vector->capacity * 2 : 4;
    while (next_capacity < capacity) {
        next_capacity *= 2;
    }

    items = realloc(vector->items, next_capacity * sizeof(*items));
    if (!items) {
        return 0;
    }

    vector->items = items;
    vector->capacity = next_capacity;
    return 1;
}

static int enact_class_vector_append(EnactClassVector *vector, EnactClass *class_value)
{
    if (!class_value || !enact_class_vector_reserve(vector, vector->count + 1)) {
        return 0;
    }

    vector->items[vector->count] = class_value;
    vector->count += 1;
    return 1;
}

static int enact_class_vector_append_unique(EnactClassVector *vector, EnactClass *class_value)
{
    if (enact_class_vector_contains(vector, class_value)) {
        return 1;
    }

    return enact_class_vector_append(vector, class_value);
}

static int enact_class_direct_superclasses(EnactClass *class_value, EnactClassVector *out)
{
    EnactClassLink *link;

    if (!class_value || !out) {
        return 0;
    }

    for (link = class_value->superclasses; link; link = link->next) {
        if (!enact_class_vector_append_unique(out, link->class_value)) {
            return 0;
        }
    }

    return 1;
}

static int enact_class_sequence_has_remaining(const EnactClassSequence *sequences, size_t count)
{
    size_t index;

    for (index = 0; index < count; index += 1) {
        if (sequences[index].classes && sequences[index].index < sequences[index].classes->count) {
            return 1;
        }
    }

    return 0;
}

static int enact_class_sequence_tail_contains(
    const EnactClassSequence *sequences,
    size_t count,
    EnactClass *class_value)
{
    size_t sequence_index;

    for (sequence_index = 0; sequence_index < count; sequence_index += 1) {
        const EnactClassSequence *sequence = &sequences[sequence_index];
        size_t item_index;

        if (!sequence->classes) {
            continue;
        }
        for (item_index = sequence->index + 1; item_index < sequence->classes->count; item_index += 1) {
            if (sequence->classes->items[item_index] == class_value) {
                return 1;
            }
        }
    }

    return 0;
}

static EnactClass *enact_class_sequence_first_candidate(EnactClassSequence *sequences, size_t count)
{
    size_t index;

    for (index = 0; index < count; index += 1) {
        const EnactClassVector *classes = sequences[index].classes;

        if (classes && sequences[index].index < classes->count) {
            return classes->items[sequences[index].index];
        }
    }

    return NULL;
}

static EnactClass *enact_class_sequence_next_candidate(EnactClassSequence *sequences, size_t count)
{
    size_t index;

    for (index = 0; index < count; index += 1) {
        const EnactClassVector *classes = sequences[index].classes;
        EnactClass *candidate;

        if (!classes || sequences[index].index >= classes->count) {
            continue;
        }

        candidate = classes->items[sequences[index].index];
        if (!enact_class_sequence_tail_contains(sequences, count, candidate)) {
            return candidate;
        }
    }

    return NULL;
}

static void enact_class_sequence_drop_candidate(EnactClassSequence *sequences, size_t count, EnactClass *candidate)
{
    size_t index;

    for (index = 0; index < count; index += 1) {
        const EnactClassVector *classes = sequences[index].classes;

        while (classes && sequences[index].index < classes->count &&
               classes->items[sequences[index].index] == candidate) {
            sequences[index].index += 1;
        }
    }
}

static int enact_class_linearization_vector(
    EnactClass *class_value,
    EnactClassVector *out,
    int allow_inconsistent,
    int *consistent);

static int enact_class_merge_linearizations(
    EnactClassVector *linearizations,
    const EnactClassVector *direct_superclasses,
    EnactClassVector *out,
    int allow_inconsistent,
    int *consistent)
{
    EnactClassSequence *sequences;
    size_t count;
    size_t index;
    int ok = 0;

    if (!direct_superclasses || !out || !consistent) {
        return 0;
    }

    count = direct_superclasses->count;
    if (count == 0) {
        return 1;
    }

    sequences = calloc(count + 1, sizeof(*sequences));
    if (!sequences) {
        return 0;
    }

    for (index = 0; index < count; index += 1) {
        sequences[index].classes = &linearizations[index];
    }
    sequences[count].classes = direct_superclasses;

    while (enact_class_sequence_has_remaining(sequences, count + 1)) {
        EnactClass *candidate = enact_class_sequence_next_candidate(sequences, count + 1);

        if (!candidate) {
            *consistent = 0;
            if (!allow_inconsistent) {
                ok = 1;
                goto done;
            }
            candidate = enact_class_sequence_first_candidate(sequences, count + 1);
        }
        if (!candidate || !enact_class_vector_append_unique(out, candidate)) {
            goto done;
        }

        enact_class_sequence_drop_candidate(sequences, count + 1, candidate);
    }

    ok = 1;

done:
    free(sequences);
    return ok;
}

static int enact_class_linearization_vector(
    EnactClass *class_value,
    EnactClassVector *out,
    int allow_inconsistent,
    int *consistent)
{
    EnactClassVector direct_superclasses = {0};
    EnactClassVector *linearizations = NULL;
    size_t index;
    int ok = 0;

    if (!class_value || !out || !consistent) {
        return 0;
    }
    if (!enact_class_vector_append_unique(out, class_value)) {
        return 0;
    }
    if (!enact_class_direct_superclasses(class_value, &direct_superclasses)) {
        return 0;
    }
    if (direct_superclasses.count == 0) {
        enact_class_vector_free(&direct_superclasses);
        return 1;
    }

    linearizations = calloc(direct_superclasses.count, sizeof(*linearizations));
    if (!linearizations) {
        enact_class_vector_free(&direct_superclasses);
        return 0;
    }

    for (index = 0; index < direct_superclasses.count; index += 1) {
        if (!enact_class_linearization_vector(
                direct_superclasses.items[index],
                &linearizations[index],
                allow_inconsistent,
                consistent)) {
            goto done;
        }
        if (!*consistent && !allow_inconsistent) {
            ok = 1;
            goto done;
        }
    }

    ok = enact_class_merge_linearizations(
        linearizations,
        &direct_superclasses,
        out,
        allow_inconsistent,
        consistent);

done:
    for (index = 0; index < direct_superclasses.count; index += 1) {
        enact_class_vector_free(&linearizations[index]);
    }
    free(linearizations);
    enact_class_vector_free(&direct_superclasses);
    return ok;
}

static int enact_class_vector_to_list(const EnactClassVector *vector, size_t start_index, EnactList **out)
{
    EnactList *list = NULL;
    size_t index;

    if (!vector || !out || start_index > vector->count) {
        return 0;
    }

    index = vector->count;
    while (index > start_index) {
        EnactValue class_value;
        EnactList *next;

        index -= 1;
        class_value = enact_value_make_class(vector->items[index]);
        next = enact_list_cons(&class_value, list);
        enact_list_release(list);
        if (!next) {
            return 0;
        }

        list = next;
    }

    *out = list;
    return 1;
}

int enact_class_linearization(EnactClass *class_value, EnactList **out)
{
    int consistent = 1;

    return enact_class_linearization_checked(class_value, out, &consistent) && consistent;
}

int enact_class_linearization_checked(EnactClass *class_value, EnactList **out, int *consistent)
{
    EnactClassVector linearization = {0};
    int is_consistent = 1;
    int ok;

    if (!class_value || !out || !consistent) {
        return 0;
    }

    *out = NULL;
    ok = enact_class_linearization_vector(class_value, &linearization, 0, &is_consistent);
    if (ok && is_consistent) {
        ok = enact_class_vector_to_list(&linearization, 0, out);
    }
    enact_class_vector_free(&linearization);
    if (!ok) {
        return 0;
    }

    *consistent = is_consistent;
    return ok;
}

int enact_class_linearization_is_consistent(EnactClass *class_value, int *out)
{
    EnactClassVector linearization = {0};
    int consistent = 1;
    int ok;

    if (!class_value || !out) {
        return 0;
    }

    ok = enact_class_linearization_vector(class_value, &linearization, 0, &consistent);
    enact_class_vector_free(&linearization);
    if (!ok) {
        return 0;
    }

    *out = consistent;
    return 1;
}

int enact_class_define_method(EnactClass *class_value, const char *name, EnactFunction *function)
{
    EnactMethod *method;
    EnactFunction *function_copy;
    char *name_copy;

    if (!class_value || !name || !function) {
        return 0;
    }

    function_copy = enact_function_retain(function);
    if (!function_copy) {
        return 0;
    }

    for (method = class_value->methods; method; method = method->next) {
        if (strcmp(method->name, name) == 0) {
            enact_function_release(method->function);
            method->function = function_copy;
            return 1;
        }
    }

    name_copy = enact_object_copy_text(name);
    if (!name_copy) {
        enact_function_release(function_copy);
        return 0;
    }

    method = calloc(1, sizeof(*method));
    if (!method) {
        free(name_copy);
        enact_function_release(function_copy);
        return 0;
    }

    method->name = name_copy;
    method->function = function_copy;
    method->next = class_value->methods;
    class_value->methods = method;
    return 1;
}

static EnactFunction *enact_class_lookup_direct_method(const EnactClass *class_value, const char *name)
{
    const EnactMethod *method;

    for (method = class_value->methods; method; method = method->next) {
        if (strcmp(method->name, name) == 0) {
            return enact_function_retain(method->function);
        }
    }

    return NULL;
}

int enact_class_lookup_method(EnactClass *class_value, const char *name, EnactFunction **out, int *consistent)
{
    EnactClassVector linearization = {0};
    EnactFunction *function;
    int is_consistent = 1;
    size_t index;

    if (!class_value || !name || !out || !consistent) {
        return 0;
    }

    *out = NULL;
    if (!enact_class_linearization_vector(class_value, &linearization, 0, &is_consistent)) {
        return 0;
    }
    if (!is_consistent) {
        enact_class_vector_free(&linearization);
        *consistent = 0;
        return 1;
    }

    for (index = 0; index < linearization.count; index += 1) {
        function = enact_class_lookup_direct_method(linearization.items[index], name);
        if (function) {
            enact_class_vector_free(&linearization);
            *out = function;
            *consistent = 1;
            return 1;
        }
    }

    enact_class_vector_free(&linearization);
    *consistent = 1;
    return 1;
}

int enact_class_method_names(const EnactClass *class_value, EnactList **out)
{
    const EnactMethod *method;
    EnactList *names = NULL;

    if (!class_value || !out) {
        return 0;
    }

    for (method = class_value->methods; method; method = method->next) {
        EnactList *next;
        EnactValue name_value;
        char *name_copy = enact_object_copy_text(method->name);

        if (!name_copy) {
            enact_list_release(names);
            return 0;
        }

        name_value = enact_value_make_atom(name_copy);
        next = enact_list_cons(&name_value, names);
        enact_value_free(&name_value);
        enact_list_release(names);
        if (!next) {
            return 0;
        }
        names = next;
    }

    *out = names;
    return 1;
}

EnactObject *enact_object_new(EnactClass *class_value)
{
    EnactObject *object;

    if (!class_value) {
        return NULL;
    }

    object = calloc(1, sizeof(*object));
    if (!object) {
        return NULL;
    }

    object->ref_count = 1;
    object->class_value = enact_class_retain(class_value);
    if (!object->class_value) {
        free(object);
        return NULL;
    }
    object->collection_kind = enact_class_collection_kind(class_value);

    return object;
}

static void enact_attribute_release_all(EnactAttribute *attribute)
{
    while (attribute) {
        EnactAttribute *next = attribute->next;

        free(attribute->name);
        enact_value_free(&attribute->value);
        free(attribute);
        attribute = next;
    }
}

EnactObject *enact_object_retain(EnactObject *object)
{
    if (!object) {
        return NULL;
    }

    object->ref_count += 1;
    return object;
}

void enact_object_release(EnactObject *object)
{
    if (!object) {
        return;
    }

    if (object->ref_count > 1) {
        object->ref_count -= 1;
        return;
    }

    enact_class_release(object->class_value);
    enact_attribute_release_all(object->attributes);
    enact_list_release(object->collection_items);
    free(object);
}

EnactClass *enact_object_class(const EnactObject *object)
{
    return object ? object->class_value : NULL;
}

EnactCollectionKind enact_object_collection_kind(const EnactObject *object)
{
    return object ? object->collection_kind : ENACT_COLLECTION_NONE;
}

EnactList *enact_object_collection_items(const EnactObject *object)
{
    return object ? object->collection_items : NULL;
}

int enact_object_define_attribute(EnactObject *object, const char *name, EnactValue value)
{
    EnactAttribute *attribute;
    char *name_copy;
    EnactValue value_copy;

    if (!object || !name) {
        return 0;
    }

    if (!enact_value_copy(&value_copy, &value)) {
        return 0;
    }

    for (attribute = object->attributes; attribute; attribute = attribute->next) {
        if (strcmp(attribute->name, name) == 0) {
            enact_value_free(&attribute->value);
            attribute->value = value_copy;
            return 1;
        }
    }

    name_copy = enact_object_copy_text(name);
    if (!name_copy) {
        enact_value_free(&value_copy);
        return 0;
    }

    attribute = calloc(1, sizeof(*attribute));
    if (!attribute) {
        free(name_copy);
        enact_value_free(&value_copy);
        return 0;
    }

    attribute->name = name_copy;
    attribute->value = value_copy;
    attribute->next = object->attributes;
    object->attributes = attribute;
    return 1;
}

int enact_object_lookup_attribute(const EnactObject *object, const char *name, EnactValue *out)
{
    const EnactAttribute *attribute;

    if (!object || !name || !out) {
        return 0;
    }

    for (attribute = object->attributes; attribute; attribute = attribute->next) {
        if (strcmp(attribute->name, name) == 0) {
            return enact_value_copy(out, &attribute->value) ? 1 : -1;
        }
    }

    return 0;
}

int enact_object_attribute_names(const EnactObject *object, EnactList **out)
{
    const EnactAttribute *attribute;
    EnactList *names = NULL;

    if (!object || !out) {
        return 0;
    }

    for (attribute = object->attributes; attribute; attribute = attribute->next) {
        EnactList *next;
        EnactValue name_value;
        char *name_copy = enact_object_copy_text(attribute->name);

        if (!name_copy) {
            enact_list_release(names);
            return 0;
        }

        name_value = enact_value_make_atom(name_copy);
        next = enact_list_cons(&name_value, names);
        enact_value_free(&name_value);
        enact_list_release(names);
        if (!next) {
            return 0;
        }
        names = next;
    }

    *out = names;
    return 1;
}
