#ifndef ENACT_OBJECT_H
#define ENACT_OBJECT_H

typedef struct EnactClass EnactClass;
typedef struct EnactObject EnactObject;

EnactClass *enact_class_new(const char *name);
EnactClass *enact_class_new_with_superclass(const char *name, EnactClass *superclass);
EnactClass *enact_class_retain(EnactClass *class_value);
void enact_class_release(EnactClass *class_value);
const char *enact_class_name(const EnactClass *class_value);
EnactClass *enact_class_superclass(const EnactClass *class_value);

EnactObject *enact_object_new(EnactClass *class_value);
EnactObject *enact_object_retain(EnactObject *object);
void enact_object_release(EnactObject *object);
EnactClass *enact_object_class(const EnactObject *object);

#endif
