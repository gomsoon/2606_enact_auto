#include <stdlib.h>
#include <string.h>

#include "object.h"

struct EnactClass {
    size_t ref_count;
    char *name;
    EnactClass *superclass;
};

struct EnactObject {
    size_t ref_count;
    EnactClass *class_value;
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
    free(object);
}

EnactClass *enact_object_class(const EnactObject *object)
{
    return object ? object->class_value : NULL;
}
