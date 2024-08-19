import re

class GScriptParser:
    def __init__(self, code):
        self.code = code
        self.tokens = self.tokenize(code)
        self.position = 0
        self.plugins = {}
        self.functions = {}

    def tokenize(self, code):
        token_specification = [
            ('NUMBER',   r'\d+(\.\d*)?'),
            ('ASSIGN',   r'='),
            ('END',      r';'),
            
            ('RETURN',   r'return'),
            ('IF',       r'if'),
            ('ELSE',     r'else'),
            ('WHILE',    r'while'),
            ('FOR',      r'for'),
            ('FUNCTION', r'function'),
            
            ('LE',       r'<'),
            ('LEQ',       r'<='),
            ('GE',       r'>'),
            ('GEQ',       r'>='),
            ('EQ',       r'=='),
            
            ('ID',       r'[A-Za-z]+'),
            
            ('OP',       r'[+\-*/]'),
            ('LPAREN',   r'\('),
            ('RPAREN',   r'\)'),
            ('LBRACE',   r'\{'),
            ('RBRACE',   r'\}'),
            ('COMMA',    r','),
            ('STRING',   r'"[^"]*"'),
            ('NEWLINE',  r'\n'),
            ('SKIP',     r'[ \t]+'),
            ('MISMATCH', r'.'),
        ]
        tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
        tokens = []
        for mo in re.finditer(tok_regex, code):
            kind = mo.lastgroup
            value = mo.group()
            if kind != 'SKIP' and kind != 'NEWLINE':
                tokens.append((kind, value))
        return tokens

    def register_plugin(self, plugin):
        self.plugins[plugin.__name__] = plugin(self)
        
    def get_plugin(self, plugin):
        return self.plugins[plugin.__name__]

    def parse(self):
        ast = []
        while self.position < len(self.tokens):
            token = self.tokens[self.position]
            for name in self.plugins:
                plugin = self.plugins[name]
                result = plugin.parse()
                # print("parse:", plugin, self.position, token, result)
                if result is not None:
                    # print("parse:", plugin, self.position, token, result)
                    ast.append(result)
                    break
            else:
                message = f'Unexpected token {token} at position {self.position}'
                print(message)
                raise RuntimeError(message)
        return ast

class AssignmentParser:
    def __init__(self, main_parser) -> None:
        self.main_parser = main_parser
        
    def parse(self):
        main_parser = self.main_parser
        tokens = main_parser.tokens
        position = main_parser.position
        
        result = self.parse_expression(tokens, position)
        if result is not None:
            new_postion = result[1]
            if new_postion < len(tokens) and tokens[new_postion][0]=='END':
                new_postion+=1
            main_parser.position = new_postion
            return result[0]
        else:
            return None
    
    def parse_expression(self, tokens, position):
        if tokens[position][0] == 'ID':
            var_name = tokens[position][1]
            position += 1
            if tokens[position][0] == 'ASSIGN':
                position += 1
                
                if tokens[position][0]=='NUMBER':
                    return (('ASSIGN', var_name, tokens[position][1]), position+1)
                
                func = self.main_parser.get_plugin(FunctionCallParser)
                result = func.parse_expression(tokens, position)
                if result:
                    var_value = result[0]
                    new_position  = result[1]
                    if tokens[new_position][0] == 'END':
                        return (('ASSIGN', var_name, var_value), new_position+1)
                    else:
                        assert False
                
                exp = ExpressionParser(self.main_parser)
                result = exp.parse_expression(tokens, position)
                if result:
                    var_value = result[0]
                    new_position  = result[1]
                    if tokens[new_position][0] == 'END':
                        return (('ASSIGN', var_name, var_value), new_position+1)
                    else:
                        print(result, tokens[new_position])
                        assert False
                
        return None

class ArithmeticExpressionParser:
    def __init__(self, main_parser) -> None:
        self.main_parser = main_parser
        
    def parse(self):
        main_parser = self.main_parser
        tokens = main_parser.tokens
        position = main_parser.position
        result = self.parse_expression(tokens, position)
        if result is not None:
            new_postion = result[1]
            if new_postion < len(tokens) and tokens[new_postion][0]=='END':
                new_postion+=1
            main_parser.position = new_postion
            
            return ('EXPR', result[0])
        return None

    def parse_expression(self, tokens, position):
        result = self.parse_term(tokens, position)
        
        if result is None:
            return None
        
        position = result[1]
        while result is not None and position < len(tokens) and tokens[position][0] == 'OP' and tokens[position][1] in '+-':
            op = tokens[position][1]
            term_result = self.parse_term(tokens, position+1)
            if term_result is None:
                break
            
            result = (op, result[0], term_result[0])
            position = term_result[1]
        
        return (result, position)

    def parse_term(self, tokens, position):
        result = self.parse_factor(tokens, position)
        if result is None:
            return None
        
        position = result[1]
        while result is not None and position < len(tokens) and tokens[position][0] == 'OP' and tokens[position][1] in '*/':
            op = tokens[position][1]
            factor_result = self.parse_factor(tokens, position+1)
            if factor_result is None:
                return None
            result = (op, result[0], factor_result[0])
            position = factor_result[1]
            
        return result
        
    def parse_factor(self, tokens, position):
        if tokens[position][0] == 'NUMBER':
            return (int(tokens[position][1]), position + 1)
        elif tokens[position][0] == 'LPAREN':
            position += 1
            result = self.parse_expression(tokens, position)
            if result is not None and tokens[result[1]][0] == 'RPAREN':
                return (result[0], result[1])
        elif tokens[position][0] == 'ID':
            return (tokens[position][1], position + 1)
        return None

class CommaExpressionParser:
    def __init__(self, main_parser) -> None:
        self.main_parser = main_parser
        
    def parse(self):
        main_parser = self.main_parser
        tokens = main_parser.tokens
        position = main_parser.position
        result = self.parse_expression(tokens, position)
        if result is not None:
            new_postion = result[1]
            if new_postion < len(tokens) and tokens[new_postion][0]=='END':
                new_postion+=1
            main_parser.position = new_postion
            return result
        return None
    
    def parse_expression(self, tokens, position):
        comma_exps = []
        
        if position<len(tokens) and tokens[position][0]=="STRING":
            result = tokens[position]
            comma_exps.append(result)
            position+=1
        else:
            exp = ArithmeticExpressionParser(self.main_parser)
            result = exp.parse_expression(tokens, position)
            if result is None:
                return None
            comma_exps.append(result)
            position = result[1]
            
        while position < len(tokens) and tokens[position][0] == 'COMMA':
            exp = ArithmeticExpressionParser(self.main_parser)
            next_result = exp.parse_expression(tokens, position+1)
            if next_result is None:
                break
            
            position = next_result[1]
            comma_exps.append(next_result)
        
        if len(comma_exps)==1:
            return (result, position)
        return (('COMMA', comma_exps), position)
    
class VarExpressionParser:
    def __init__(self, main_parser) -> None:
        self.main_parser = main_parser
        
    def parse(self):
        main_parser = self.main_parser
        tokens = main_parser.tokens
        position = main_parser.position
        
        result = self.parse_expression(tokens, position)
        if result is not None:
            new_postion = result[1]
            if new_postion < len(tokens) and tokens[new_postion][0]=='END':
                new_postion+=1
            main_parser.position = new_postion
            return ("VAR", result[0])
        else:
            return None
        
    def parse_expression(self, tokens, position):
        if tokens[position][0] == 'ID' and tokens[position][1] == 'var':
            assign = AssignmentParser(self.main_parser)
            result = assign.parse_expression(tokens, position+1)
            if result:
                return result
            
            exp = ExpressionParser(self.main_parser)
            result = exp.parse_expression(tokens, position+1)
            if result:
                return result
            
        return None

class ExpressionParser:
    def __init__(self, main_parser) -> None:
        self.main_parser = main_parser
        
    def parse(self):
        main_parser = self.main_parser
        tokens = main_parser.tokens
        position = main_parser.position
        result = self.parse_expression(tokens, position)
        if result is not None:
            new_postion = result[1]
            if new_postion < len(tokens) and tokens[new_postion][0]=='END':
                new_postion+=1
            main_parser.position = new_postion
            return result[0]
        else:
            return None
    
    def parse_expression(self, tokens, position):
        c = CommaExpressionParser(self.main_parser)
        return c.parse_expression(tokens, position)
    
class BodyParser:
    def __init__(self, main_parser, left, right) -> None:
        self.main_parser = main_parser
        self.left = left
        self.right = right
    
    def parse(self):
        tokens = self.main_parser.tokens
        position = self.main_parser.position
        result = self.parse_expression(tokens, position)
        if result is not None:
            new_postion = result[1]
            if new_postion < len(tokens) and tokens[new_postion][0]=='END':
                new_postion+=1
            self.main_parser.position = new_postion
            return result[0]
        else:
            return None
        
    def parse_expression(self, tokens, position):
        body = []
        if tokens[position][0] == self.left:
            position += 1
            
            while tokens[position][0] != self.right:
                plugins = self.main_parser.plugins
                for name in plugins:
                    plugin = plugins[name]
                    if isinstance(plugin, FunctionParser):
                        continue
                    
                    result = plugin.parse_expression(tokens, position)
                    
                    if result is not None:
                        body.append(result[0])
                        position = result[1]
                        if position<len(tokens) and tokens[position][0]=='END':
                            position+=1
                        break
                
            if position<len(tokens) and tokens[position][0]==self.right:
                position+=1
            
            return (("BLOCK", body), position)

class ConditionParser:
    def __init__(self, main_parser) -> None:
        self.main_parser = main_parser
        
    def parse(self):
        main_parser = self.main_parser
        tokens = main_parser.tokens
        position = main_parser.position
        
        result = self.parse_expression(tokens, position)
        if result is not None:
            new_postion = result[1]
            if new_postion < len(tokens) and tokens[new_postion][0]=='END':
                new_postion+=1
            main_parser.position = new_postion
            return result[0]
        else:
            return None

    def parse_expression(self, tokens, position):
        
        if tokens[position][0] == 'IF':
            position += 1
            
            if tokens[position][0] == 'LPAREN':
                position += 1
                
                expr_parser = CompareParaer(self.main_parser)
                condition, new_position = expr_parser.parse_expression(tokens, position)
                
                if condition is not None:
                    
                    
                    
                    
                    position = new_position
                    if tokens[position][0] == 'RPAREN':
                        position += 1
                        
                        body_parser = BodyParser(self.main_parser, "LBRACE", "RBRACE")
                        body_result = body_parser.parse_expression(tokens, position)
                        
                        
                        if body_result is not None:
                            body_if, new_position = body_result[0], body_result[1]
                            position = new_position
            
                            if position<len(tokens) and tokens[position][0] == 'ELSE':
                                position += 1
                                
                                body_parser = BodyParser(self.main_parser, "LBRACE", "RBRACE")
                                body_result = body_parser.parse_expression(tokens, position)
                                if body_result is not None:
                                    body_else, new_position = body_result[0], body_result[1]
                                    return (('CONDITION', condition, body_if, body_else), new_position)
                            else:
                                return (('CONDITION', condition, body_if, None), new_position)
      
        return None
    
class CompareParaer:
    def __init__(self, main_parser) -> None:
        self.main_parser = main_parser
        
    def parse(self):
        main_parser = self.main_parser
        tokens = main_parser.tokens
        position = main_parser.position
        
        result = self.parse_expression(tokens, position)
        if result is not None:
            new_postion = result[1]
            if new_postion < len(tokens) and tokens[new_postion][0]=='END':
                new_postion+=1
            main_parser.position = new_postion
            return result[0]
        else:
            return None
        
    def parse_expression(self, tokens, position):
        exp_left = ExpressionParser(self.main_parser)
        exp_right = ExpressionParser(self.main_parser)
        
        left = exp_left.parse_expression(tokens, position)
        if left is not None:
            op_left, position = left
            if position<len(tokens) and tokens[position][0] in ['LE','LEQ', 'GE', 'GEQ', 'EQ']:
                op = tokens[position][1]
                position+=1
                right = exp_right.parse_expression(tokens, position)
                if right is not None:
                    op_right, position = right
                    return (("COMPARE", op, op_left, op_right), position)
        
        return None

class LoopParser:
    def __init__(self, main_parser) -> None:
        self.main_parser = main_parser
        
    def parse(self):
        main_parser = self.main_parser
        tokens = main_parser.tokens
        position = main_parser.position
        
        result = self.parse_expression(tokens, position)
        if result is not None:
            new_postion = result[1]
            if new_postion < len(tokens) and tokens[new_postion][0]=='END':
                new_postion+=1
            main_parser.position = new_postion
            return result[0]
        else:
            return None
        
    def parse_expression(self, tokens, position):
        if tokens[position][0] == 'WHILE':
            position += 1
            if tokens[position][0] == 'LPAREN':
                position += 1
                expr_parser = CompareParaer(self.main_parser)
                condition, new_position = expr_parser.parse_expression(tokens, position)
                if condition is not None:
                    position = new_position
                    if tokens[position][0] == 'RPAREN':
                        position += 1
                        
                        body_parser = BodyParser(self.main_parser, "LBRACE", "RBRACE")
                        body_result = body_parser.parse_expression(tokens, position)
                        if body_result is not None:
                            body, new_position = body_result[0], body_result[1]
                            (('WHILE', condition, body), new_position)
                            
        elif tokens[position][0] == 'FOR':
            position += 1
            if tokens[position][0] == 'LPAREN':
                position += 1
                
                assign_parser = AssignmentParser(self.main_parser)
                init, new_position = assign_parser.parse_expression(tokens, position)
                
                if init is not None:
                    position = new_position
                    
                    expr_parser = CompareParaer(self.main_parser)
                    condition, new_position = expr_parser.parse_expression(tokens, position)
                    if condition is not None:
                        position = new_position
                        if tokens[position][0] == 'END':
                            position += 1
                            
                            assign_parser = AssignmentParser(self.main_parser)
                            increment, new_position = assign_parser.parse_expression(tokens, position)
                            if increment is not None:
                                position = new_position
                                if tokens[position][0] == 'RPAREN':
                                    position += 1
                                    
                                    body_parser = BodyParser(self.main_parser, "LBRACE", "RBRACE")
                                    body_result = body_parser.parse_expression(tokens, position)
                                    if body_result is not None:
                                        body, new_position = body_result[0], body_result[1]
                                        (('FOR', init, condition, increment, body), new_position)
        return None

class ReturnParser:
    def __init__(self, main_parser) -> None:
        self.main_parser = main_parser
        
    def parse(self):
        main_parser = self.main_parser
        tokens = main_parser.tokens
        position = main_parser.position
        
        result = self.parse_expression(tokens, position)
        if result is not None:
            new_postion = result[1]
            if new_postion < len(tokens) and tokens[new_postion][0]=='END':
                new_postion+=1
            main_parser.position = new_postion
            return result[0]
        else:
            return None

    def parse_expression(self, tokens, position):
        if tokens[position][0] == 'RETURN':
            position += 1
            
            expr_parser = ExpressionParser(self.main_parser)
            expr, new_position = expr_parser.parse_expression(tokens, position)
            
            if expr is not None:
                return (('RETURN', expr), new_position)
        
        return None
        
class FunctionParser:
    def __init__(self, main_parser) -> None:
        self.main_parser = main_parser
        self.functions = self.main_parser.functions
        
    def parse(self):
        main_parser = self.main_parser
        tokens = main_parser.tokens
        position = main_parser.position
        result = self.parse_expression(tokens, position)
        if result is not None:
            new_postion = result[1]
            if new_postion < len(tokens) and tokens[new_postion][0]=='END':
                new_postion+=1
            main_parser.position = new_postion
            return result[0]
        else:
            return None

    def parse_expression(self, tokens, position):
        # 解析函数定义
        if tokens[position][0] == 'FUNCTION':
            position += 1
            
            if tokens[position][0] == 'ID':
                func_name = tokens[position][1]
                position += 1
                
                if tokens[position][0] == 'LPAREN':
                    position += 1
                    params = []
                    
                    while tokens[position][0] != 'RPAREN':
                        if tokens[position][0] == 'ID':
                            params.append(tokens[position][1])
                            position += 1
                            if tokens[position][0] == 'RPAREN':
                                break
                            if tokens[position][0] != 'COMMA':
                                return None
                            position += 1
                        else:
                            return None
                    
                    position += 1
                    
                    body_parser = BodyParser(self.main_parser, "LBRACE", "RBRACE")
                    body_result = body_parser.parse_expression(tokens, position)
                    
                    if body_result is not None:
                        body, new_position = body_result[0], body_result[1]
                        self.functions[func_name] = (params, body)
                        return (('FUNCTION_DEF', func_name, params, body), new_position)
        return None
    
class FunctionCallParser:
    def __init__(self, main_parser) -> None:
        self.main_parser = main_parser
        self.functions = self.main_parser.functions
        
    def parse(self):
        main_parser = self.main_parser
        tokens = main_parser.tokens
        position = main_parser.position
        result = self.parse_expression(tokens, position)
        if result is not None:
            new_postion = result[1]
            if new_postion < len(tokens) and tokens[new_postion][0]=='END':
                new_postion+=1
            main_parser.position = new_postion
            return result[0]
        else:
            return None

    def parse_expression(self, tokens, position):
        if tokens[position][0] == 'ID' and tokens[position][1] in self.functions:
            func_name = tokens[position][1]
            
            position += 1
            if tokens[position][0] == 'LPAREN':
                position += 1
                args = []
                
                while tokens[position][0] != 'RPAREN':
                    expr_parser = CommaExpressionParser(self.main_parser)
                    result = expr_parser.parse_expression(tokens, position)
                    arg, new_position = result
                    
                    if arg is not None:
                        args.append(arg)
                        position = new_position
                        
                        if tokens[position][0] == 'RPAREN':
                            break
                        
                        if tokens[position][0] != 'COMMA':
                            return None
                        position += 1
                    else:
                        return None
                
                return (('FUNCTION_CALL', func_name, args), position+1)
        return None

class GScriptExecutor:
    def __init__(self, ast):
        self.ast = ast
        self.variables = {}
        self.functions = {}

    def execute(self):
        for node in self.ast:
            self.execute_node(node)

    def execute_node(self, node):
        node_type = node[0]
        if node_type == 'ASSIGN':
            _, var_name, var_value = node
            self.variables[var_name] = var_value
        elif node_type == 'EXPR':
            return self.evaluate_expression(node[1])
        elif node_type == 'IF':
            _, condition, body = node
            if self.evaluate_expression(condition):
                self.execute_node(body)
        elif node_type == 'WHILE':
            _, condition, body = node
            while self.evaluate_expression(condition):
                self.execute_node(body)
        elif node_type == 'FOR':
            _, init, condition, increment, body = node
            self.execute_node(init)
            while self.evaluate_expression(condition):
                self.execute_node(body)
                self.execute_node(increment)
        elif node_type == 'PRINT':
            _, value = node
            print(self.evaluate_expression(value))
        elif node_type == 'FUNCTION_DEF':
            _, func_name, params, body = node
            self.functions[func_name] = (params, body)
        elif node_type == 'FUNCTION_CALL':
            _, func_name, args = node
            self.call_function(func_name, args)
        elif node_type == 'RETURN':
            value = self.evaluate_expression(node[1])
            return ('RETURN', value)

    def evaluate_expression(self, expr):
        if isinstance(expr, (int, float)):
            return expr
        elif isinstance(expr, str):
            return self.variables.get(expr, 0)
        elif isinstance(expr, tuple):
            if len(expr)==3:
                op, left, right = expr
                left_val = self.evaluate_expression(left)
                right_val = self.evaluate_expression(right)
                if op == '+':
                    return left_val + right_val
                elif op == '-':
                    return left_val - right_val
                elif op == '*':
                    return left_val * right_val
                elif op == '/':
                    return left_val / right_val
            else:
                return expr

    def call_function(self, func_name, args):
        if func_name in self.functions:
            params, body = self.functions[func_name]
            local_vars = self.variables.copy()
            for param, arg in zip(params, args):
                local_vars[param] = self.evaluate_expression(arg)
            executor = GScriptExecutor(body)
            executor.variables = local_vars
            executor.functions = self.functions
            executor.execute()