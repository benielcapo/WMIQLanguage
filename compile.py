import builtins
import wmi
import sys
import os

class Variables:
    def __len__(self):
        return len(self.__dict__)

class ReturnList(list):
    pass

def get_class_properties(obj):
    props = {k: v for k, v in vars(obj).items() if not callable(v)}
    return props

class Protocol:
    def __init__(self, arg_names, name, return_var_name):
        self.lines = []
        self.arg_names = arg_names
        self.name = name
        self.return_var_name = return_var_name
    def execute(self, block_name, _, wmi_obj, return_obj, protocols, var_list):
        if len(var_list) != len(self.arg_names):
            raise Exception(f"Expected {len(self.arg_names)} arguments, but got {len(var_list)}")
        func_vars = Variables()
        for i, var in enumerate(var_list):
            setattr(func_vars, self.arg_names[i], var)
        for line in self.lines:
            stripped_split = line.lstrip().split(" ")
            command = stripped_split[0].lstrip()
            try:
                getattr(Functions, command)(line.lstrip(), "", func_vars, wmi_obj, return_obj, self, protocols)
            except:
                raise Exception(f"Function {command} not found")
        return getattr(self, "return_val", None)

def handle_if(val1_, operator, val2_, block_vars):
    def resolve_value(val):
        if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
            return val[1:-1]
        elif val.lstrip('-').replace('.', '', 1).isdigit():
            return float(val) if '.' in val else int(val)
        else:
            try:
                return getattr(block_vars, val)
            except AttributeError:
                raise NameError(f"Variable '{val}' not found in block_vars")
    left = resolve_value(val1_)
    right = resolve_value(val2_)
    ops = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
    }
    if operator not in ops:
        raise ValueError(f"Invalid operator '{operator}'")
    return ops[operator](left, right)

class Functions:
    @staticmethod
    def STORE_FUNC(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj, self_protocol, protocols):
        split = line.split(" ")
        func_name = split[1]
        if split[2] == "IN":
            location = split[3]
            if split[4] == "AS":
                data_type = split[5]
                try:
                    data = getattr(builtins, data_type)()
                    try:
                        result = getattr(wmi_obj, func_name)()
                    except AttributeError:
                        succ = False
                        try:
                            result = getattr(wmi_obj, getattr(block_vars, func_name))()
                            succ = True
                        except:
                            pass
                        if not succ:
                            raise Exception(f"Class {func_name} not found in namespace {wmi_obj._namespace} or block variables")
                    except Exception as e:
                        raise Exception(f"WMI error accessing {func_name}: {e}")
                    if isinstance(data, list):
                        data = result
                    if isinstance(data, str):
                        data = str(result)
                    if isinstance(data, int):
                        try:
                            data = int(result)
                        except:
                            try:
                                data = len(result)
                            except:
                                data = sys.getsizeof(result)
                    setattr(block_vars, location, data)
                except:
                    raise Exception(f"Data type {data_type} not found")
    @staticmethod
    def STORE_LIST_ELEMENT(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj, self_protocol, protocols):
        split = line.split(" ")
        list_and_index = split[1]
        start = list_and_index.find("[")
        end = list_and_index.find("]")
        index = int(list_and_index[start+1:end])
        name = list_and_index[:start]
        try:
            var = getattr(block_vars, name)
        except:
            raise Exception(f"Variable {name} doesnt exist in the current context")
        try:
            element = var[index]
        except:
            raise Exception(f"Index {index} in {name} is out of bounds, or {name} isnt a list")
        if split[2] == "IN":
            location = split[3]
            setattr(block_vars, location, element)
    @staticmethod
    def STORE_PROP(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj, self_protocol, protocols):
        split = line.split(" ")
        var_and_prop = split[1]
        split_v_p = var_and_prop.split(".")
        name = split_v_p[0]
        prop = split_v_p[1]
        if split[2] == "IN":
            location = split[3]
            try:
                var = getattr(block_vars, name)
            except:
                raise Exception(f"Variable {name} doesnt exist in the current context")
            try:
                if prop.startswith("{") and prop.endswith("}"):
                    try:
                        var_prop = getattr(block_vars, prop[1:-1])
                        data = getattr(var, var_prop)
                    except:
                        data = getattr(var, prop)
                else:
                    data = getattr(var, prop)
            except:
                raise Exception(f"Error while getting {prop} from {name}")
            location_data_type = ""
            try:
                location_data_type = type(getattr(block_vars, location))
            except:
                pass
            if location_data_type == list or location_data_type == ReturnList:
                getattr(block_vars, location).append(data)
            setattr(block_vars, location, data)
    @staticmethod
    def ADD_RETURN(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol, protocols):
        split = line.split(" ")
        name = split[1]
        try:
            var = getattr(block_vars, name)
            return_obj.append(var)
        except:
            raise Exception(f"Variable {name} doesnt exist in the current context")
    @staticmethod
    def ITERATE_OVER(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol, protocols):
        split = line.split(" ")
        iter_target = split[1]
        func_name = split[4]
        for_var_name = split[3]
        store_name = split[-1]
        result = ReturnList()
        line_inside = " ".join(split[4:])
        func = getattr(Functions, func_name)
        try:
            variable = getattr(block_vars, iter_target)
        except:
            raise Exception(f"Variable {iter_target} doesnt exist in the current context")
        try:
            for v in variable:
                for_variables = Variables()
                setattr(for_variables, for_var_name, v)
                setattr(for_variables, store_name, result)
                func(line_inside, "", for_variables, wmi_obj, result, self_protocol, protocols)
            setattr(block_vars, store_name, list(result))
        except:
            raise Exception(f"Function {func_name} didnt exist")
    @staticmethod
    def STORE_RAW(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol, protocols):
        split = line.split(" ")
        var_name = split[1]
        try:
            data = getattr(block_vars, var_name)
        except:
            raise Exception(f"Variable {var_name} doesnt exist in the current context")
        location = split[3]
        location_data_type = ""
        try:
            location_data_type = type(getattr(block_vars, location))
        except:
            pass
        if location_data_type == list or location_data_type == ReturnList:
            getattr(block_vars, location).append(data)
        setattr(block_vars, location, data)
    @staticmethod
    def RANGE(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol, protocols):
        split = line.split(" ")
        start = split[1]
        end = split[2]
        location = split[-1]
        try:
            range_obj = list(range(int(start), int(end)))
        except:
            raise Exception(f"Either start({start}) or end({end}) arent valid integers")
        setattr(block_vars, location, range_obj)
    @staticmethod
    def STORE_STR(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol, protocols):
        split = line.split(" ")
        content = " ".join(split[1:-2])
        location = split[-1]
        if location == "":
            split = split[:-1]
            location = split[-1]
            content = " ".join(split[1:-2])
        setattr(block_vars, location, content)
    @staticmethod
    def PRINT(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol, protocols):
        split = line.split(" ")
        content = " ".join(split[1:])
        if content.startswith("'") or content.startswith('"'):
            print(content[1:-1])
        else:
            try:
                var = getattr(block_vars, content)
                print(var)
            except:
                raise Exception(f"Variable {content} doesnt exist in the current context")
    @staticmethod
    def ARIT(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol, protocols):
        split = line.split(" ")
        operation = " ".join(split[1:-2])
        location = split[-1]
        result = eval(operation, {}, get_class_properties(block_vars))
        setattr(block_vars, location, result)
    @staticmethod
    def STORE_INT(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol, protocols):
        split = line.split(" ")
        num = split[1]
        location = split[3]
        try:
            setattr(block_vars, location, int(num))
        except:
            raise Exception(f"{num} is not a valid int")
    @staticmethod
    def IF(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol, protocols):
        split = line.split(" ")
        end_condition = line.find("{")
        condition = " ".join(split[1:end_condition])
        condition = condition[:condition.find("{")]
        if condition.endswith(" "):
            condition = condition[:-1]
        split_con = condition.split(" ")
        val1 = split_con[0]
        operator = split_con[1]
        val2 = split_con[2]
        brackets_inside = line[line.index("{"):line.index("}")].removeprefix("{").removeprefix(" ").removesuffix(" ")
        do_if = brackets_inside.split(" | ")
        result = handle_if(val1, operator, val2, block_vars)
        if result == True:
            try:
                do_if_true = do_if[0]
                func_name = do_if_true.split(" ")[0]
                getattr(Functions, func_name)(do_if_true, block_name, block_vars, wmi_obj, return_obj, self_protocol, protocols)
            except IndexError:
                pass
        else:
            try:
                do_if_false = do_if[1]
                func_name = do_if_false.split(" ")[0]
                getattr(Functions, func_name)(do_if_false, block_name, block_vars, wmi_obj, return_obj, self_protocol, protocols)
            except IndexError:
                pass
    @staticmethod
    def TRY(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol, protocols):
        split = line.split(" ")
        brackets_inside = line[line.index("{"):line.index("}")].removeprefix("{").removeprefix(" ").removesuffix(" ")
        func_name = brackets_inside.split(" ")[0]
        location = split[-1]
        result = []
        try:
            getattr(Functions, func_name)(brackets_inside, block_name, block_vars, wmi_obj, return_obj, self_protocol, protocols)
            result.append(0)
            result.append("")
        except Exception as err:
            result.append(-1)
            result.append(str(err))
        setattr(block_vars, location, result)
    @staticmethod
    def STORE_FLOAT(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol, protocols):
        split = line.split(" ")
        location = split[-1]
        float_str = split[1]
        setattr(block_vars, location, float(float_str))
    @staticmethod
    def STORE_NONE(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol, protocols):
        split = line.split(" ")
        location = split[-1]
        setattr(block_vars, location, None)
    @staticmethod
    def OPEN(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol, protocols):
        split = line.split(" ")
        location = split[-1]
        file_name = " ".join(split[1:-2])
        if file_name.startswith("'") or file_name.startswith('"'):
            file_name = file_name.removeprefix("'").removeprefix('"').removesuffix("'").removesuffix('"')
            with open(file_name) as f:
                try:
                    setattr(block_vars, location, f.read())
                except UnicodeDecodeError:
                    raise UnicodeDecodeError(f"{file_name} is binary data!")
        else:
            try:
                file_name = getattr(block_vars, file_name)
                with open(file_name) as f:
                    try:
                        setattr(block_vars, location, f.read())
                    except UnicodeDecodeError:
                        raise UnicodeDecodeError(f"{file_name} is binary data!")
            except:
                raise FileNotFoundError(f"File {file_name} doesnt exist")
    @staticmethod
    def WRITE_FILE(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol, protocols):
        before_after = line.removeprefix("WRITE_FILE ").split(" IN ")
        content = before_after[0]
        file = before_after[1]
        actual_content = ""
        actual_file = ""
        if file.startswith("'") or file.startswith('"') and file.endswith("'") or file.endswith('"'):
            actual_file = file.removeprefix("'").removeprefix('"').removesuffix("'").removesuffix('"')
        else:
            try:
                actual_file = str(getattr(block_vars, file, ""))
            except:
                raise Exception(f"Variable {file} doesnt exist in the current context")
        if content.startswith("'") or content.startswith('"') and content.endswith("'") or content.endswith('"'):
            actual_content = content.removeprefix("'").removeprefix('"').removesuffix("'").removesuffix('"')
        else:
            try:
                actual_content = str(getattr(block_vars, content, ""))
            except:
                raise Exception(f"Variable {content} doesnt exist in the current context")
        with open(actual_file, "w+") as f:
            f.write(actual_content)
    @staticmethod
    def RETURN_PROTO(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol, protocols):
        if self_protocol is None:
            raise Exception("Tried to call RETURN_PROTO outside a protocol")
        try:
            self_protocol.return_val = getattr(block_vars, line.split(" ")[1])
        except:
            raise Exception("Error returning proto")
    @staticmethod
    def CALL_PROTO(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList, self_protocol: Protocol, protocols: dict[str, Protocol]):
        split = line.split(" ")
        proto_name = split[1]
        start_args = line.index("(")
        end_args = line.index(")")
        args = line[start_args:end_args + 1].removeprefix("(").removesuffix(")")
        pass_args = []
        location = split[-1]
        for arg in args.split(","):
            arg_name = arg.removeprefix(" ")
            try:
                pass_args.append(getattr(block_vars, arg_name))
            except:
                raise Exception(f"Variable {arg_name} doesnt exist in the current context")
        try:
            proto = protocols[proto_name]
            proto.execute(block_name, block_vars, wmi_obj, return_obj, self_protocol, pass_args)
        except KeyError:
            raise Exception("Protocol " + str(proto_name) + " doesnt exist")
        result = proto.execute(block_name, block_vars, wmi_obj, return_obj, protocols, pass_args)
        setattr(block_vars, location, result)

def compile(wmiq_code, ignore_lazy_errors=False, allow_prints=False):
    protocols = {}
    variables = Variables()
    data = wmiq_code
    lines = data.split("\n")
    block = ""
    in_protocol = False
    protocol_name = ""
    block_vars = None
    block_wmi_obj = None
    return_data_name = ""
    for line in lines:
        if line.strip() == "":
            continue
        if block_vars is not None and len(block_vars) == 0:
            raise Exception("Length is 0, line is " + str(line))
        just_set_block = False
        if line.lstrip().startswith("#"):
            continue
        stripped_split = line.lstrip().split(" ")
        split = line.split(" ")
        if split[0] == "RETURN_DATA":
            if return_data_name != "":
                raise Exception("A RETURN_DATA already existed (" + str(return_data_name) + ")")
            setattr(variables, split[1], ReturnList())
            return_data_name = split[1]
        if allow_prints:
            print("length of " + str(split) + " is " + str(len(split)))
            print(split[0] + " starts with P- is " + str(split[0].startswith("P-")) + ". also line is " + str(line))
        if len(split) == 1 or split[0].startswith("P-"):
            if allow_prints:
                print("does " + str(split[0]) + " end with : " + str(split[0].endswith(":")))
            if line.endswith(":"):
                block = split[0][:-1]
                if allow_prints:
                    print(split[0] + " starts with P- is " + str(split[0].startswith("P-")))
                if split[0].startswith("P-"):
                    in_protocol = True
                    protocol_name = split[0].split('-', 1)[1]
                    protocol_args = " ".join(split[2:]).removesuffix(":")
                    args = protocol_args.removeprefix("(").removesuffix(")")
                    args = args.split(",")
                    new_args = []
                    for arg in args:
                        new_args.append(arg.removeprefix(" ").removesuffix(" "))
                    return_location = split[-1].removesuffix(":")
                    if allow_prints:
                        print("args defining protocol: " + str(new_args))
                    protocols[protocol_name] = Protocol(new_args, protocol_name, return_location)
                    continue
                if block == "NULL":
                    block_wmi_obj = wmi.WMI()
                else:
                    block_wmi_obj = wmi.WMI(namespace=block)
                just_set_block = True
                if allow_prints:
                    print("set block to " + str(block) + " and block_wmi_obj to " + str(block_wmi_obj))
            else:
                pass
        indent = len(line) - len(line.lstrip())
        if indent == 4:
            if in_protocol:
                protocols[protocol_name].lines.append(line.lstrip())
                continue
            if block_vars == None:
                block_vars = Variables()
            command = stripped_split[0].lstrip()
            if command.strip() == "":
                continue
            if block_wmi_obj is None:
                block_wmi_obj = wmi.WMI()
            if allow_prints:
                print("passing " + str(block_vars.__dict__))
            if not ignore_lazy_errors:
                try:
                    getattr(Functions, command)(line.lstrip(), block, block_vars, block_wmi_obj, getattr(variables, return_data_name), None, protocols)
                except:
                    raise Exception(f"Function {command} not found")
            else:
                getattr(Functions, command)(line.lstrip(), block, block_vars, block_wmi_obj, getattr(variables, return_data_name), None, protocols)
        else:
            if not in_protocol and not just_set_block and not line.strip().startswith("P-"):
                block = ""
                block_vars = None
                block_wmi_obj = None
            if in_protocol and (line.strip() == "" or not line.startswith("    ")):
                in_protocol = False
                protocol_name = False
    try:
        return getattr(variables, return_data_name)
    except:
        return []
