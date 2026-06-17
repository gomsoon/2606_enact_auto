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

struct EnactClass {
    size_t ref_count;
    char *name;
    EnactClass *superclass;
    EnactMethod *methods;
};

struct EnactObject {
    size_t ref_count;
    EnactClass *class_value;
    EnactAttribute *attributes;
};

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

EnactClass *enact_class_new(const char *name)
{
    return enact_class_new_with_superclass(name, NULL);
}

EnactClass *enact_class_new_with_superclass(const char *name, EnactClass *superclass)
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
    class_value->superclass = enact_class_retain(superclass);
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
    enact_class_release(class_value->superclass);
    free(class_value);
}

const char *enact_class_name(const EnactClass *class_value)
{
    return class_value ? class_value->name : "";
}

EnactClass *enact_class_superclass(const EnactClass *class_value)
{
    return class_value ? class_value->superclass : NULL;
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

EnactFunction *enact_class_lookup_method(const EnactClass *class_value, const char *name)
{
    const EnactClass *current;
    const EnactMethod *method;

    if (!class_value || !name) {
        return NULL;
    }

    for (current = class_value; current; current = current->superclass) {
        for (method = current->methods; method; method = method->next) {
            if (strcmp(method->name, name) == 0) {
                return enact_function_retain(method->function);
            }
        }
    }

    return NULL;
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
    free(object);
}

EnactClass *enact_object_class(const EnactObject *object)
{
    return object ? object->class_value : NULL;
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
