grammar Flo;

CR : '\n';
COMMENT
    : '/*' .*? '*/' -> channel(HIDDEN);
LINE_COMMENT
    : '//' ~('\n'|'\r')* '\r'? '\n' -> channel(HIDDEN);
WHITESPACE : ( '\t' | ' ' | '\r' | CR| '\u000C' )+ -> channel(HIDDEN);
//all numbers are represented by a single 'num' type in the grammar:
NUMBER:[0-9]+;

//operators;
PLUS	:	'+';
MINUS	:	'-';
MULT	:	'*';
DIV	:	'/';
MOD	:	'%';
EQUALS  :       '=';
NEGATION :      '!';
BINDTO :      '->';
PUTVALUE :    '<-';
DOT :      '.';
COLON: ':';
OR: 'or';
AND: 'and';

//punctuation
LCB     :       '{';
RCB     :       '}';
LPAREN : '(';
RPAREN : ')';
COMMA  :	',';

//keywords
DEC : 'dec';
MODULE: 'module';
COMPONENT: 'component';
NEW: 'new';
INPUT: 'input';
OUTPUT: 'output';

//primitaves
STRING:('"' ~('"')* '"') | ('\'' ~('\'')* '\'');
BOOL:'true' | 'false';
ID :('a'..'z'|'A'..'Z'|'0'..'9'|'_')+;
SPACE: ' ';

atom: STRING #string 
	| NUMBER #number
	| BOOL #bool
	| ID #id
	| atom DOT atom #getAttrib;

declaration: 
	(DEC (INPUT|OUTPUT)? ID COLON ID) #simpleDeclaration
	|(DEC (INPUT|OUTPUT)? ID COLON ID EQUALS compound_expression) #computedDeclaration;

compound_expression_paren
	:
		atom
		| LPAREN compound_expression RPAREN
	;

compound_expression_not
	:
		compound_expression_paren 
		|
		NEGATION compound_expression_mult_div 
	;

compound_expression_mult_div
	:
		compound_expression_not
		(
			MULT  compound_expression_plus_minus 
			| DIV  compound_expression_plus_minus
			| MOD compound_expression_plus_minus 
		)*
	;
	
compound_expression_plus_minus
	:
		compound_expression_mult_div
		(
			PLUS compound_expression_and 
			| MINUS compound_expression_and
		)*
	;

compound_expression_and
	:
		compound_expression_plus_minus
		(
			AND compound_expression_or
		)*	
	;
	
compound_expression_or
	:
		compound_expression_and
		(
			OR compound_expression_putvalue
		)*	
	;

compound_expression_putvalue
	:
		compound_expression_or
		(
			PUTVALUE compound_expression
		)*	
	;

compound_expression: 
	compound_expression_putvalue 
	(
		BINDTO compound_expression_putvalue
	)*
;

statement: declaration | compound_expression;

component: COMPONENT ID LCB (statement)* RCB;

module: MODULE ID LCB (component | statement)* RCB ;