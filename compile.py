import builtins
import wmi
import sys

class Variables:
    pass

class ReturnList(list):
    pass

def get_class_properties(obj):
    props = {k: v for k, v in vars(obj).items() if not callable(v)}
    return props

def handle_if(val1_, operator, val2_, block_vars):
    def resolve_value(val):
        if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
            return val[1:-1]
        elif val.lstrip('-').isdigit():
            return int(val)
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
    result = ops[operator](left, right)
    return result

class Functions:
    @staticmethod
    def STORE_FUNC(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj):
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
    def STORE_LIST_ELEMENT(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj):
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
    def STORE_PROP(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj):
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
    def ADD_RETURN(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList):
        split = line.split(" ")
        name = split[1]
        try:
            var = getattr(block_vars, name)
            return_obj.append(var)
        except:
            raise Exception(f"Variable {name} doesnt exist in the current context")
    @staticmethod
    def ITERATE_OVER(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList):
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
                func(line_inside, "", for_variables, wmi_obj, result)
            setattr(block_vars, store_name, list(result))
        except:
            raise Exception(f"Function {func_name} didnt exist")
    @staticmethod
    def STORE_RAW(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList):
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
    def RANGE(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList):
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
    def STORE_STR(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList):
        split = line.split(" ")
        content = " ".join(split[1:-2])
        location = split[-1]
        if location == "":
            split = split[:-1]
            location = split[-1]
            content = " ".join(split[1:-2])
        setattr(block_vars, location, content)
    @staticmethod
    def PRINT(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList):
        split = line.split(" ")
        content = " ".join(split[1:])
        if content.startswith("'") or content.startswith('"'):
            print(content[1:-1])
        else:
            try:
                var = getattr(block_vars, content)
                print(var)
            except:
                print(block_vars.__dict__)
                raise Exception(f"Variable {content} doesnt exist in the current context")
    @staticmethod
    def ARIT(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList):
        split = line.split(" ")
        operation = " ".join(split[1:-2])
        location = split[-1]
        result = eval(operation, {}, get_class_properties(block_vars))
        setattr(block_vars, location, result)
    @staticmethod
    def STORE_INT(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList):
        split = line.split(" ")
        num = split[1]
        location = split[3]
        try:
            setattr(block_vars, location, int(num))
        except:
            raise Exception(f"{num} is not a valid int")
    @staticmethod
    def IF(line: str, block_name: str, block_vars: Variables, wmi_obj, return_obj: ReturnList):
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
        brackets_inside = line[line.index("{"):line.index("}")].removeprefix("{").removeprefix(" ").removeprefix(" ")
        do_if = brackets_inside.split(" | ")
        result = handle_if(val1, operator, val2, block_vars)
        if result == True:
            try:
                do_if_true = do_if[0]
                func_name = do_if_true.split(" ")[0]
                getattr(Functions, func_name)(do_if_true, block_name, block_vars, wmi_obj, return_obj)
            except IndexError:
                pass
        else:
            try:
                do_if_false = do_if[1]
                func_name = do_if_false.split(" ")[0]
                getattr(Functions, func_name)(do_if_false, block_name, block_vars, wmi_obj, return_obj)
            except IndexError:
                pass

def compile(wmiq_code, ignore_lazy_errors=False, allow_prints=False):
    variables = Variables()
    data = wmiq_code
    lines = data.split("\n")
    block = ""
    block_vars = None
    block_wmi_obj = None
    return_data_name = ""
    for line in lines:
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
        if len(split) == 1:
            if allow_prints:
                print("does " + str(split[0]) + " end with : " + str(split[0].endswith(":")))
            if split[0].endswith(":"):
                block = split[0][:-1]
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
            if block_vars == None:
                block_vars = Variables()
            command = stripped_split[0].lstrip()
            if command.strip() == "":
                continue
            if not ignore_lazy_errors:
                try:
                    getattr(Functions, command)(line.lstrip(), block, block_vars, block_wmi_obj, getattr(variables, return_data_name))
                except:
                    raise Exception(f"Function {command} not found")
            else:
                getattr(Functions, command)(line.lstrip(), block, block_vars, block_wmi_obj, getattr(variables, return_data_name))
        else:
            if just_set_block:
                continue
            if block_vars or block:
                block = ""
                block_vars = None
                block_wmi_obj = None
    return getattr(variables, return_data_name)
