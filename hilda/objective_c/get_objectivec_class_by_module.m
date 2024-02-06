@import ObjectiveC;
@import Foundation;

uintptr_t *classList = (uintptr_t *)__objc_class_list;
size_t count = (int)__count_objc_class;
NSMutableDictionary *classDictionary = [NSMutableDictionary dictionaryWithCapacity:count];

for (size_t i = 0; i < count; i++) {
    Class cls = (Class)classList[i];
    NSString *className = NSStringFromClass(cls);

    if (cls && className) {
        NSNumber *classAddress = [NSNumber numberWithUnsignedLongLong:(uintptr_t)cls];
        [classDictionary setObject:classAddress forKey:className];
    }
}

NSData *data = [NSJSONSerialization dataWithJSONObject:classDictionary options:0 error:nil];
[[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];