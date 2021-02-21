@import ObjectiveC;
@import Foundation;
unsigned int outCount = 0;
unsigned int i = 0, j = 0;

Class objcClass = (Class)__class_address__;
if (!objcClass) {
    objcClass = objc_getClass("__class_name__");
}

NSDictionary *classDescription = @{
    @"protocols": [NSMutableArray new],
    @"ivars": [NSMutableArray new],
    @"properties": [NSMutableArray new],
    @"methods": [NSMutableArray new],
    @"name": [NSString stringWithCString:class_getName(objcClass) encoding:NSUTF8StringEncoding],
    @"address": [NSNumber numberWithLong:(uintptr_t)objcClass],
    @"super": [NSNumber numberWithLong:(uintptr_t)class_getSuperclass(objcClass)],
};

id *protocols = class_copyProtocolList(objcClass, &outCount);
for (i = 0; i < outCount; ++i) {
    [classDescription[@"protocols"] addObject: [NSString stringWithCString:protocol_getName(protocols[i]) encoding:NSUTF8StringEncoding]];
}
if (protocols) {
    free(protocols);
}

Ivar *ivars = class_copyIvarList(objcClass, &outCount);
for (i = 0; i < outCount; ++i) {
    [classDescription[@"ivars"] addObject:@{
        @"name": [NSString stringWithCString:ivar_getName(ivars[i]) encoding:NSUTF8StringEncoding],
        @"type": [NSString stringWithCString:ivar_getTypeEncoding(ivars[i]) encoding:NSUTF8StringEncoding],
        @"offset": [NSNumber numberWithInt:ivar_getOffset(ivars[i])],
    }];
}
if (ivars) {
    free(ivars);
}

NSMutableArray *fetchedProperties = [NSMutableArray new];
NSString *propertyName;
objc_property_t *properties = class_copyPropertyList(objcClass, &outCount);
for (i = 0; i < outCount; ++i) {
    propertyName = [NSString stringWithCString:property_getName(properties[i]) encoding:NSUTF8StringEncoding];
    if ([fetchedProperties containsObject:propertyName]) {
        continue;
    }
    else {
        [fetchedProperties addObject:propertyName];
    }
    [classDescription[@"properties"] addObject:@{
        @"name": propertyName,
        @"attributes": [NSString stringWithCString:property_getAttributes(properties[i]) encoding:NSUTF8StringEncoding],
    }];
}
if (properties) {
    free(properties);
}

Method *methods = class_copyMethodList(object_getClass(objcClass), &outCount);
unsigned int argsCount;
NSMutableArray *argsTypes;
char *methodArgumentsTypes;
char *methodReturnType;
for (i = 0; i < outCount; ++i) {
    argsCount = method_getNumberOfArguments(methods[i]);
    argsTypes = [NSMutableArray new];
    for (j = 0; j < argsCount; ++j) {
        methodArgumentsTypes = method_copyArgumentType(methods[i], j);
        [argsTypes addObject: [NSString stringWithCString:methodArgumentsTypes encoding:NSUTF8StringEncoding]];
        if (methodArgumentsTypes) {
            free(methodArgumentsTypes);
        }
    }
    methodReturnType = method_copyReturnType(methods[i]);
    [classDescription[@"methods"] addObject:@{
        @"name": [NSString stringWithCString:sel_getName(method_getName(methods[i])) encoding:NSUTF8StringEncoding],
        @"address": [NSNumber numberWithLong:(uintptr_t)method_getImplementation(methods[i])],
        @"is_class": @YES,
        @"type": [NSString stringWithCString:method_getTypeEncoding(methods[i]) encoding:NSUTF8StringEncoding],
        @"return_type": [NSString stringWithCString:methodReturnType encoding:NSUTF8StringEncoding],
        @"args_types": argsTypes,
    }];
    if (methodReturnType) {
        free(methodReturnType);
    }
}
if (methods) {
    free(methods);
}

methods = class_copyMethodList(objcClass, &outCount);
for (i = 0; i < outCount; ++i) {
    argsCount = method_getNumberOfArguments(methods[i]);
    argsTypes = [NSMutableArray new];
    for (j = 0; j < argsCount; ++j) {
        methodArgumentsTypes = method_copyArgumentType(methods[i], j);
        [argsTypes addObject: [NSString stringWithCString:methodArgumentsTypes encoding:NSUTF8StringEncoding]];
        if (methodArgumentsTypes) {
            free(methodArgumentsTypes);
        }
    }
    methodReturnType = method_copyReturnType(methods[i]);
    [classDescription[@"methods"] addObject:@{
        @"name": [NSString stringWithCString:sel_getName(method_getName(methods[i])) encoding:NSUTF8StringEncoding],
        @"address": [NSNumber numberWithLong:(uintptr_t)method_getImplementation(methods[i])],
        @"is_class": @NO,
        @"type": [NSString stringWithCString:method_getTypeEncoding(methods[i]) encoding:NSUTF8StringEncoding],
        @"return_type": [NSString stringWithCString:methodReturnType encoding:NSUTF8StringEncoding],
        @"args_types": argsTypes,
    }];
    if (methodReturnType) {
        free(methodReturnType);
    }
}
if (methods) {
    free(methods);
}

NSData *data = [NSJSONSerialization dataWithJSONObject:classDescription options:0 error:nil];
[[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
