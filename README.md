# gscript

create a simple script language by using gpt

## example

```python
from gscript import AssignmentParser
from gscript import ExpressionParser
from gscript import ConditionParser
from gscript import LoopParser
from gscript import FunctionParser
from gscript import FunctionCallParser
from gscript import GScriptParser
from gscript import GScriptExecutor
from gscript import ReturnParser
from gscript import VarExpressionParser


if __name__=="__main__":
    test_cases = [
        
        # func
        """
        function print(){
            
        }
        """,
        
        # func with body
        """
        function add(a, b) {
            return a + b;
        }
        """,
        
        # var and assgin
        """
        var x = 5;
        var y = 3;
        """,
        
        # func and assign, and fun call
        """
        function add(a, b) {
            return a + b;
        }
        var x = 5;
        var y = 3;
        var result = add(x, y);
        """,
        
        # condition
        """
        function print(){
            
        }
        if (result > 5) {
            print("Result is greater than 5");
        }
        """,
        
        # condition with else
        """
        function print(){
            
        }
        if (result > 5) {
            print("Result is greater than 5");
        } else {
            print("Result is 5 or less");
        }
        """,
        
        # all
        """
        function print(a){
            
        }
        
        function add(a, b) {
            return a + b;
        }
        var x = 5;
        var y = 3;
        var result = add(x, y);
        
        if (result > 5) {
            print("Result is greater than 5");
        } else {
            print("Result is 5 or less");
        }
        """
    ]
    
    
    for code in test_cases:
        parser = GScriptParser(code)
        parser.register_plugin(FunctionParser)
        parser.register_plugin(FunctionCallParser)
        parser.register_plugin(ReturnParser)
        parser.register_plugin(ConditionParser)
        parser.register_plugin(LoopParser)
        parser.register_plugin(VarExpressionParser)
        parser.register_plugin(AssignmentParser)
        parser.register_plugin(ExpressionParser)
        ast = parser.parse()
        print(ast)
```
