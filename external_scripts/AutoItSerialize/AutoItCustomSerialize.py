# DeprecationWarning
# this script was used to serialize autoit on python but now we are using javascript middleware

import re
import numpy as np


def Serialize(event_name, *params):
    serialized_str = _serialize([event_name, [*params] if len(params) > 0 else np.int32(0)])
    removed_0x = serialized_str[:-1]
    return removed_0x.encode()

def UnSerialize(source: bytes) -> list[list[str, list]]:
    """
    this function will unserialize autoitsocketio4 from autoit to python

    :params source: bytes from autoit
    :returns events: all events of this package -- with args:['event', [*args]] -- without args:['event', 0]
    """
    source_str = source.decode()
    source_str = re.sub(r"(?s)(.*)\#$", r"\1", source_str) # Remove last strap of package load (Can be 1 to n)
    packages = source_str.split('#')
    events = []
    for package in packages:
        event_payload = _unserialize(package)
        events.append(event_payload)
    return events



def _serialize(source, glue="#"):
    if isinstance(source, list):
        return f"a|{_serialize_array(source)}{glue}"
    elif isinstance(source, bool):
        return f"b|{1 if source else 0}{glue}"
    elif isinstance(source, str):
        return f"s|0x{bytes.hex(source.encode())}{glue}"
    elif isinstance(source, np.int32):
        return f"Int32|{source}{glue}"
    elif isinstance(source, np.int64):
        return f"Int64|{source}{glue}"
    elif isinstance(source, bytes):
        return f"Binary|{source}{glue}"
    elif isinstance(source, float):
        return f"Double|{source}{glue}"
    else:
        print("ERROR on _serialize") # TODO

        

def _serialize_array(array: list) -> str:
    serialized = ""
    for item in array:
        serialized += _serialize(item, '$')
    if len(array) > 0:
        serialized = serialized[:-1]
    return f"0x{bytes.hex(serialized.encode())}"



# Func __Serialize_UnSerializeArray(Const $array)
# 	Local Const $payload = BinaryToString($array)
# 	Local Const $parts = StringSplit($payload, "$")
# 	Local $aNew[$parts[0]]

# 	For $i = 1 To $parts[0]
# 		$aNew[$i - 1] = _UnSerialize($parts[$i])
# 	Next

# 	Return $aNew
# EndFunc   ;==>__Serialize_UnSerializeArray

def _unserialize_array(array: hex):
    payload = bytes.fromhex(array[2:]).decode()
    parts = payload.split('$')
    new = []
    for part in parts:
        new.append(_unserialize(part))
    return new


def _unserialize(package: str):
    parts = package.split('#')

    for part in parts:
        typ, val, = part.split('|')
        
        match typ:
            case "s":
                return bytes.fromhex(val[2:]).decode()
            case "a":
                return _unserialize_array(val)
            # case "o":
            #     return __Serialize_UnSerializeScriptingDictionary($val) # TODO
            case "b":
                return val == 1
            case "Int32":
                return np.int32(val)
            case "Int64":
                return np.int64(val)
            case "Binary":
                return val.encode()
            case "Double":
                return float(val)
            case "Keyword":
                return None


# Func _UnSerialize(Const $source)
    # Local Const $parts = StringSplit($source, "#")

    # For $i = 1 To $parts[0]
    #     Local $part = StringSplit($parts[$i], '|', 2)
        # Local $type = $part[0]
        # Local $val = $part[1]

#         Switch $type
#             Case "s"
#                 Return BinaryToString($val)
#             Case "a"
#                 Return __Serialize_UnSerializeArray($val)
#             Case "o"
#                 Return __Serialize_UnSerializeScriptingDictionary($val)
#             Case "b"
#                 Return $val == 1
#             Case "Int32"
#                 Return Number($val, 1)
#             Case "Int64"
#                 Return Number($val, 2)
#             Case "Ptr"
#                 Return Ptr($val)
#             Case "Binary"
#                 Return Binary($val)
#             Case "Double"
#                 Return Number($val, 3)
#             Case "Keyword"
#                 Return Null
#         EndSwitch

#     Next

# EndFunc   ;==>UnSerialize
