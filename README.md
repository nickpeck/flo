# Flo Language Runtime

Flo is a toy language of my own design, used as a test-bed for some ideas and creative thinking in language runtime implementation.

In a nutshell, it abandons some common ideals in favor of a reactive, flow-based paradigm, that could be said to more closely model the architecture of an electrical circuit. I wonder if this approach might be better suited to certain categories of computation (digital signal manipulation, or neural network implementation). In some ways, this seemingly introduces a set of limitations to the programmer, but I might encourage us to consider that language paradigms are in fact defined by their limitations, rather than their features (Robert C. Martin).

It is modeled in Python, and allows a range of imports from external Python modules and the Python standard library.

_does the world need another language?_ probably not... But plagued with an inquisitive mind I like to follow through concepts just to see where they lead.. What if...? Maybe theres something to be learnt here that might feed back into my own practice of established languages and runtimes.

## Quick Overview

### Hello World!
The customary "Hello world" can be expressed thus:
~~~
module main {
    stdout <- "hello, world!"
}
~~~
Hopefully, this should be relatively self-apparent, other than that program entry points are expected to take place under the namespace of 'module main'. The operator <- is used to write the evaluation of the right hand expression into the variable on the left. In this case, stdout is one of several built-ins automatically ported from the Python standard library (sys.stdout).

The contents are saved to a text file named with a .flo extension and executed using:
python -m flo myfile.flo

### Thinking In Streams
To illustrate a fundamental difference between flo and most conventional language paradigms, lets consider the following, written in Python:
~~~
a = 4
b = 3
c = a + b
print(c) # 7
a = 6
print(c) # 7
~~~

However, if this were Flo, the state of 'c' would be quite different (the following is not Flo syntax, more on that shortly):
~~~
a = 4
b = 3
c = a + b
print(c) # 7
a = 6
print(c) # 9
~~~

Variable 'c' became a computed value that always holds the state of the sum of its two dependencies (a and b). You might prefer to think of all variables as actually being streams, which can be connected together, using pipes into different dependency chains.

Therefore, the 'state' of the application is something that you _model_, but not something that we directly control. I would say that the state is an _emergent property_.

In fact, there is no way to directly interact with, or predict the state of the application as a whole, at any given time, as all of these pipes operate in an asynchronous manner. We can only reason about _evental consistency_. The success of the application depends upon the strength of the modeled relationships between the stated entities.

Before we move on, lets write that previous example in Flo syntax:

~~~
module main {
    dec {
        a = 4
        b = 3
        c = a + b
    }
    c -> stdout
    a <- 6
}
~~~
The new language features introduced here, are:
- All 'variables' must be declared at the start of the module, before we actually interact with them in any way. This takes place with the dec keyword.
- Variables can take a type declaration, (which is redundant at the present time), but in the future will offer static-type checking, as the related python tools for this mature. (a : int = 4)
- a and b were initialized with default values. These are optional, but note that these variables will not notify their observers until a concrete value is written to them.
- 'c' is what we call a 'Computed' variable (more on this later, see 'connecting streams'). A computed variable must be declared in the dec block (because the pipes operate in an asynchronous manner, we cannot declare new ones after the fact).
- The operator '->' binds the state of one variable to another, so in this case, we are declaring a binding between c, and stdout (ie, as c is recomputed, the value will be pushed to standard output)

### Connecting Streams
Let us consider the different ways in which streams are connected.

_computed_ : we can create a new stream that is the computed state of a given set of dependencies
~~~
dec {
    a : int = 4
    b : int = 3
    c : int = a + b // c is a computed variable
}
~~~
_join_ : we can join two streams (a,b) to create a third stream c that contains all state changes of a or b.
~~~
dec {
    a : int = 4
    b : int = 3
    c : int = a & b // the single ampersand here denotes a join
}
~~~
_filter_ : we can apply a filter to a stream, resulting in a new stream that only contains values that pass a given filter expressions
~~~
dec {
    a : int = 4
    b : int = a|a > 4 // reads as, filter the events of a, where value of a is greater than 4
}
~~~
_bind_: we can bind a stream 'a' to another 'b' so that changes to a are written to 'b'
~~~
dec {
    a : int = 4
    b : int
}
a -> b // a is bound to b
~~~

### Primitive Types
Flo supports the following types (all of which are wrappers around their native Python equivalents)
~~~
// numbers
1
1.5
0.001

// strings
"Hello world"

// booleans
true, false

// tuples (there is no list type, as flo values are technically immutable by design)
(1,)
(1, 2, 4, "hello world")

// dictionaries
{"a" : 1, "b" : {"c" : "hello"}}
~~~

Dictionaries and tuples support simple index lookups (of single values only at present), as per python:
~~~
(1, 2, 3, "hello world")[3]
... "hello world"
{"a" : 1, "b" : {"c" : "hello"}}["b"]["c"]
... "hello world"
{"a" : 1, 0 : 2}[0]
... 2
~~~

### Operators and Expressions
Many operators and expressions are borrowed from Python syntax. There are a few differences. Here is a summary:
~~~
a + b // addition
a - b // subtraction
a * b // multiplication
a / b // division
a % b // modulus
a > b // greater than
a < b // less than
a >= b // greater than or equal to
a <= b // less than or equal to
!a // negation (not a)
a or b // or
a and b //and
a -> b // bind a to b (all changes to a are written to b)
a <- b // put the current value of b in a
a|a > 5 // filter all future values of a where a is greater than 5
a & b // join and b (resulting in a new stream)
~~~

### Feedback Loop!
You may have spotted an obvious danger in this design. What if one were to specify a relationship such as:
~~~
module main {
    dec {
        x : int
        y : int = x * x
    }
    y -> stdout
    y -> x
    x <- 2
}
~~~
... y is a computed variable that depends upon x, but we are then declaring a binding between y and x. This would create a runaway cyclic dependency chain (feedback loop) that would, (under the current implementation), stall the interpreter.

Flo keeps track of the dependency chains in your declarations and will raise an Exception at runtime, before attempting to connect such a dependency graph.

It is under consideration that such an effect might serve a purpose (just as it might in a multi-stage transistor amplifier), and that a keyword might allow the user to overrule this behavior. This will require some evaluation and changes to the runtime.

### Program Structure
Preserving the idea of an electric system as our basis, the primary structural components are Modules and Components.

A _module_ is analogous to a standard breadboard, and may contain a number of components
A _component_ has many similarities to a Module, but allows re-use (and polymorphism, coming soon).

~~~
module main {
    component adder {
        dec {
            x : int
            y : int
            z : int = x+y
        }
    }
    dec a : adder # a new instance of the adder component
    a.z -> stdout # access attribes within the scope of a
    a.x <- 8
    a.y <- 9
}
~~~

### Imports
Flow currently allows imports of Python (functions, and builtin functions only at present).

Imports are bound to specific modules, and happen at the start of a module, or component declaration. These are wrapped as streams, so inherit the behaviors discussed earlier:
~~~
module main {
    uses math
    math.ceil -> stdout # all functions under the math namespace are wrapped in streams
    math.ceil  <- 1.75
}
~~~

## Rebuilding the Antlr lexer/parser
Antlr 4 is used to generate the language parser. (You'll need antlr-4.7-complete.jar)
After updating flo\flo.g4, run the following from the root folder to rebuild the lexer and parser:
~~~
java -jar antlr\antlr-4.7-complete.jar -package flo -Dlanguage=Python3 flo\Flo.g4
~~~

## Further Reading
see test_parser.py for various test cases that illustrate the evolving nature of the language.
