import json

from hilda.lldb_importer import lldb


def dirlist(path: str):
    hilda = lldb.hilda_client
    return json.loads(hilda.po(f'''
    NSArray *objectData = [[NSFileManager defaultManager] contentsOfDirectoryAtPath:@"{path}" error:Nil];
    NSData *data = [NSJSONSerialization dataWithJSONObject:objectData options:0 error:nil];
    [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
    '''))
