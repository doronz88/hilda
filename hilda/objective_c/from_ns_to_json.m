@import Foundation;

__block NSObject *(^make_json_serializable)(NSObject *, BOOL isKey);

NSArray *(^make_json_serializable_array)(NSArray *) = ^(NSArray *src) {
    NSMutableArray *result = [NSMutableArray new];
    [src enumerateObjectsUsingBlock:^(id obj, NSUInteger idx, BOOL * stop) {
        [result addObject:make_json_serializable(obj, NO)];
    }];
    return result;
};

NSDictionary *(^make_json_serializable_dictionary)(NSDictionary *) = ^(NSDictionary *src) {
    NSMutableDictionary *result = [NSMutableDictionary new];
    [src enumerateKeysAndObjectsUsingBlock:^(id key, id  obj, BOOL * stop) {
        result[(NSString *)make_json_serializable(key, YES)] = make_json_serializable(obj, NO);
    }];
    return result;
};

make_json_serializable = ^(NSObject *obj, BOOL isKey) {
    if ([obj isKindOfClass:[NSSet class]]) {
        obj = [(NSSet *)obj allObjects];
    }
    if ([obj isKindOfClass:[NSDictionary class]]) {
        obj = (NSObject *)(make_json_serializable_dictionary((NSDictionary *)obj));
    }
    if ([obj isKindOfClass:[NSArray class]]) {
        obj = (NSObject *)(make_json_serializable_array((NSArray *)obj));
    }
    if ([obj isKindOfClass:[NSData class]]) {
        obj = (NSObject *)[NSString
            stringWithFormat:@"__hilda_magic_key__|NSData|%@", [(NSData *)obj base64EncodedStringWithOptions:0]
        ];
    }
    if ([obj isKindOfClass:[NSDate class]]) {
        obj = (NSObject *)[NSString
            stringWithFormat:@"__hilda_magic_key__|NSDate|%@",
            [NSNumber numberWithDouble: [(NSDate *)obj timeIntervalSince1970]]
        ];
    }
    if (!isKey || [obj isKindOfClass:[NSString class]]) {
        return obj;
    }
    if ([obj isKindOfClass:[NSDictionary class]] || [obj isKindOfClass:[NSArray class]]) {
        NSData *jsonData = [NSJSONSerialization dataWithJSONObject:obj options:0 error:nil];
        NSString *jsonDump = [[NSString alloc] initWithData:jsonData encoding:NSUTF8StringEncoding];
        NSString *type = [obj isKindOfClass:[NSDictionary class]] ? @"NSDictionary" : @"NSArray";
        return (NSObject *) [NSString
            stringWithFormat:@"__hilda_magic_key__|%@|%@", type, jsonDump
        ];
    }
    if ([obj isKindOfClass:[NSNumber class]]) {
        return (NSObject *) [NSString
            stringWithFormat:@"__hilda_magic_key__|NSNumber|%@", [(NSNumber *)obj stringValue]
        ];
    }
    if ([obj isKindOfClass:[NSNull class]]) {
        return (NSObject *) [NSString stringWithFormat:@"__hilda_magic_key__|NSNull|"];
    }
    return obj;
};
NSDictionary *wrapper = @{@"root": (NSObject *)__ns_object_address__};
wrapper = make_json_serializable_dictionary(wrapper);
NSData *jsonData = [NSJSONSerialization dataWithJSONObject:wrapper options:0 error:nil];
[[NSString alloc] initWithData:jsonData encoding:NSUTF8StringEncoding];
