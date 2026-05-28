import ast
import inspect
import textwrap

class GotoTransformer(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        node.decorator_list = []  # Избавляемся от рекурсии
        
        new_body = []
        # Стартовое состояние
        new_body.append(ast.Assign(
            targets=[ast.Name(id='_state', ctx=ast.Store())],
            value=ast.Constant(value='start')
        ))
        
        current_label = 'start'
        block_body = []

        for stmt in node.body:
            # Если встретили метку label.имя
            if (isinstance(stmt, ast.Expr) and 
                isinstance(stmt.value, ast.Attribute) and 
                isinstance(stmt.value.value, ast.Name) and 
                stmt.value.value.id == 'label'):
                
                if block_body:
                    # Закрываем старый блок: если стейт совпадает, выполняем код
                    # Если код дошел до конца блока без явного goto, переключаем стейт на СЛЕДУЮЩУЮ метку
                    new_body.append(ast.If(
                        test=ast.Compare(left=ast.Name(id='_state', ctx=ast.Load()), ops=[ast.Eq()], comparators=[ast.Constant(value=current_label)]),
                        body=block_body + [ast.Assign(targets=[ast.Name(id='_state', ctx=ast.Store())], value=ast.Constant(value=stmt.value.attr))],
                        orelse=[]
                    ))
                current_label = stmt.value.attr
                block_body = []
            else:
                # Магия поиска goto.имя внутри любых if/else
                class SuperGotoReplacer(ast.NodeTransformer):
                    def visit_If(self, if_node):
                        # Рекурсивно обрабатываем внутренности if/else
                        self.generic_visit(if_node)
                        
                        # А теперь пересобираем тело и ветку else, раскрывая goto
                        if_node.body = self.expand_gotos(if_node.body)
                        if_node.orelse = self.expand_gotos(if_node.orelse)
                        return if_node
                        
                    def expand_gotos(self, body_list):
                        new_list = []
                        for s in body_list:
                            if (isinstance(s, ast.Expr) and 
                                isinstance(s.value, ast.Attribute) and 
                                isinstance(s.value.value, ast.Name) and 
                                s.value.value.id == 'goto'):
                                
                                target = s.value.attr
                                # Вставляем ДВЕ инструкции вместо одной: стейт + CONTINUE
                                new_list.append(ast.Assign(
                                    targets=[ast.Name(id='_state', ctx=ast.Store())],
                                    value=ast.Constant(value=target)
                                ))
                                new_list.append(ast.Continue())
                            else:
                                new_list.append(s)
                        return new_list
                
                # Запускаем глубокий поиск и подмену во всех ветвлениях
                stmt = SuperGotoReplacer().visit(stmt)
                
                # Если сам stmt на верхнем уровне является goto (редко, но вдруг)
                if (isinstance(stmt, ast.Expr) and 
                    isinstance(stmt.value, ast.Attribute) and 
                    isinstance(stmt.value.value, ast.Name) and 
                    stmt.value.value.id == 'goto'):
                    block_body.append(ast.Assign(targets=[ast.Name(id='_state', ctx=ast.Store())], value=ast.Constant(value=stmt.value.attr)))
                    block_body.append(ast.Continue())
                else:
                    block_body.append(stmt)
        
        # Закрываем последний блок функции
        if block_body:
            new_body.append(ast.If(
                test=ast.Compare(left=ast.Name(id='_state', ctx=ast.Load()), ops=[ast.Eq()], comparators=[ast.Constant(value=current_label)]),
                body=block_body + [ast.Break()], 
                orelse=[]
            ))

        # Оборачиваем все блоки IF в бесконечный while
        while_node = ast.While(
            test=ast.Constant(value=True),
            body=new_body[1:], 
            orelse=[]
        )
        
        node.body = [new_body[0], while_node]
        return ast.fix_missing_locations(node)


def cursed_zone(func):
    source = inspect.getsource(func)
    source = textwrap.dedent(source)
    
    tree = ast.parse(source)
    transformer = GotoTransformer()
    new_tree = transformer.visit(tree)
    
    code_obj = compile(new_tree, filename=inspect.getfile(func), mode='exec')
    
    namespace = func.__globals__
    local_env = {}
    
    exec(code_obj, namespace, local_env)
    return local_env[func.__name__]