import json
from hilda.objective_c_symbol import ObjectiveCSymbol


def dirlist(self, path):
    return json.loads(self.po(f'''
    NSArray *objectData = [[NSFileManager defaultManager] contentsOfDirectoryAtPath:@"{path}" error:Nil];
    NSData *data = [NSJSONSerialization dataWithJSONObject:objectData options:0 error:nil];
    [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
    '''))
