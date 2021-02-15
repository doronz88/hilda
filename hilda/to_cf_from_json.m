@import Foundation;

__block NSObject *(^convertHildaMagics)(NSObject *);

convertHildaMagics = ^(NSObject *src) {
    if ([src isKindOfClass:[NSMutableDictionary class]]) {
        [(NSMutableDictionary *)src enumerateKeysAndObjectsUsingBlock:^(id key, id  obj, BOOL * stop) {
            [(NSMutableDictionary *)src setObject:convertHildaMagics((NSObject *)obj) forKey:key];
        }];
        return src;
    }
    if ([src isKindOfClass:[NSMutableArray class]]) {
        [(NSMutableArray *)src enumerateObjectsUsingBlock:^(id obj, NSUInteger idx, BOOL * stop) {
            ((NSMutableArray *)src)[idx] = convertHildaMagics((NSObject *)obj);
        }];
        return src;
    }
    if (![src isKindOfClass:[NSString class]]) {
        return src;
    }
    if (![(NSString *)src hasPrefix:@"__hilda_magic_key__"]) {
        return src;
    }
    NSArray *srcItems = [(NSString *)src componentsSeparatedByString:@"|"];
    if ([(NSString *)srcItems[1] isEqualToString:@"NSData"]){
        return (NSObject *)[[NSData alloc] initWithBase64EncodedString:(NSString *)srcItems[2] options:0];
    }
    if ([(NSString *)srcItems[1] isEqualToString:@"NSDate"]){
        return (NSObject *)[NSDate dateWithTimeIntervalSince1970:[(NSString *)srcItems[2] doubleValue]];
    }
    return src;
};

NSString *s = @"__json_object_dump__";
NSData *jsonData = [s dataUsingEncoding:NSUTF8StringEncoding];
NSError *error;
NSMutableDictionary *jsonObject = [
    NSJSONSerialization JSONObjectWithData:jsonData options:NSJSONReadingMutableContainers error: &error
];
jsonObject = convertHildaMagics(jsonObject);
[jsonObject objectForKey:@"root"];