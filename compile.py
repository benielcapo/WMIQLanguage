import builtins
import wmi
import sys

class Variables:
    pass

class ReturnList(list):
    pass

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
                        raise Exception(f"Class {func_name} not found in namespace {wmi_obj._namespace}")
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
            print("set " + str(element) + " as " + str(location))
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
                data = getattr(var, prop)
            except:
                raise Exception(f"Error while getting {prop} from {name}")
            location_data_type = ""
            try:
                location_data_type = type(getattr(block_vars, location))
            except:
                pass
            print(location + " is " + str(location_data_type))
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
                print("iterating over " + str(v) + " of " + str(variable))
                for_variables = Variables()
                setattr(for_variables, for_var_name, v)
                setattr(for_variables, store_name, result)
                print("variables are " + str(for_variables.__dict__) + " and result is " + str(result.__dict__))
                func(line_inside, "", for_variables, wmi_obj, result)
                print("after calling the function, variables are " + str(for_variables.__dict__) + " and result is " + str(result.__dict__))
            print("gave block variables " + str(list(result)))
            setattr(block_vars, store_name, list(result))
        except:
            raise Exception(f"Function {func_name} didnt exist")

def compile(wmiq_code, ignore_lazy_errors=False):
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
        print("length of " + str(split) + " is " + str(len(split)))
        if len(split) == 1:
            print("does " + str(split[0]) + " end with : " + str(split[0].endswith(":")))
            if split[0].endswith(":"):
                block = split[0][:-1]
                if block == "NULL":
                    block_wmi_obj = wmi.WMI()
                else:
                    block_wmi_obj = wmi.WMI(namespace=block)
                just_set_block = True
                print("set block to " + str(block) + " and block_wmi_obj to " + str(block_wmi_obj))
            else:
                pass
        indent = len(line) - len(line.lstrip())
        if indent == 4:
            if block_vars == None:
                block_vars = Variables()
            command = stripped_split[0].lstrip()
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
