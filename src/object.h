#ifndef ENACT_OBJECT_H
#define ENACT_OBJECT_H

typedef struct EnactClass EnactClass;
typedef struct EnactObject EnactObject;
typedef struct EnactFunction EnactFunction;
typedef struct EnactValue EnactValue;
typedef struct EnactList EnactList;

typedef enum {
    ENACT_COLLECTION_NONE,
    ENACT_COLLECTION_SET,
    ENACT_COLLECTION_BAG
} EnactCollectionKind;

EnactClass *enact_class_new(const char *name);
EnactClass *enact_class_new_with_superclass(const char *name, EnactClass *superclass);
EnactClass *enact_class_new_with_superclasses(const char *name, EnactList *superclasses);
EnactClass *enact_class_retain(EnactClass *class_value);
void enact_class_release(EnactClass *class_value);
const char *enact_class_name(const EnactClass *class_value);
EnactClass *enact_class_superclass(const EnactClass *class_value);
int enact_class_superclasses(const EnactClass *class_value, EnactList **out);
int enact_class_linearization(EnactClass *class_value, EnactList **out);
int enact_class_linearization_checked(EnactClass *class_value, EnactList **out, int *consistent);
int enact_class_linearization_is_consistent(EnactClass *class_value, int *out);
int enact_class_define_method(EnactClass *class_value, const char *name, EnactFunction *function);
int enact_class_lookup_method(EnactClass *class_value, const char *name, EnactFunction **out, int *consistent);
int enact_class_method_names(const EnactClass *class_value, EnactList **out);
int enact_class_bad_attribute_names(const EnactClass *class_value, EnactList **out);

EnactObject *enact_object_new(EnactClass *class_value);
EnactObject *enact_object_retain(EnactObject *object);
void enact_object_release(EnactObject *object);
EnactClass *enact_object_class(const EnactObject *object);
EnactCollectionKind enact_object_collection_kind(const EnactObject *object);
EnactList *enact_object_collection_items(const EnactObject *object);
EnactObject *enact_object_copy_with_collection_items(const EnactObject *object, EnactList *items);
int enact_object_define_attribute(EnactObject *object, const char *name, EnactValue value);
int enact_object_lookup_attribute(const EnactObject *object, const char *name, EnactValue *out);
int enact_object_attribute_names(const EnactObject *object, EnactList **out);

#endif
