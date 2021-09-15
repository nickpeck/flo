grammar Flo;

CR : '\n';
COMMENT
    : '/*' .*? '*/' -> channel(HIDDEN);
LINE_COMMENT
    : '//' ~('\n'|'\r')* '\r'? '\n' -> channel(HIDDEN);
WHITESPACE : ( '\t' | ' ' | '\r' | CR| '\u000C' )+ -> channel(HIDDEN);
//all numbers are represented by a single 'num' type in the grammar:
NUMBER: [0-9]+('.'[0-9]+)? | ('.'[0-9]+) | [0]+ '.'[0-9]+ ;

//operators;
PLUS	:	'+';
MINUS	:	'-';
MULT	:	'*';
DIV	:	'/';
MOD	:	'%';
EQUALS  :       '=';
EQUALITY:       '==';
GTR:       '>';
LESS:       '<';
GTREQ:       '>=';
LESSEQ:       '<=';
NEGATION :      '!';
BINDTO :      '->';
PUTVALUE :    '<-';
DOT :      '.';
COLON: ':';
OR: 'or';
AND: 'and';
FILTER: '|';
JOIN: '&';

//punctuation
LCB     :       '{';
RCB     :       '}';
LSB     :       '[';
RSB     :       ']';
LPAREN : '(';
RPAREN : ')';
COMMA  :	',';

//keywords
DEC : 'dec';
MODULE: 'module';
COMPONENT: 'component';
NEW: 'new';
PUBLIC: 'public';
IMPORT: 'uses';
FROM: 'from';
AS: 'as';
SYNC: 'sync';

//primitaves
STRING:('"' ~('"')* '"') | ('\'' ~('\'')* '\'');
BOOL:'true' | 'false';
ID :('a'..'z'|'A'..'Z'|'0'..'9'|'_')+;
SPACE: ' ';
//ERR_CHAR : . ;

atom: STRING #string 
	| NUMBER #number
	| BOOL #bool
	| ID #id
	| atom (DOT atom)+ #getAttrib
	| atom (LSB (NUMBER|STRING) RSB)+ #index
	| ( LPAREN compound_expression COMMA RPAREN 
		| LPAREN compound_expression (COMMA compound_expression)+ RPAREN) #tuple
//	| listexpr #atom_list
	| dictexpr #atom_dict;

//listexpr : ( LSB compound_expression (COMMA compound_expression)* RSB);

dictexpr: LCB STRING COLON atom
	(COMMA STRING COLON atom )* RCB;

import_statement:
	(IMPORT ID (DOT ID)*)
	| (FROM ID (DOT ID)* IMPORT (ID)*)
	(AS ID)?;

simpleDeclaration:
	((PUBLIC)? ID (COLON ID)?)
;

computedDeclaration:
	((PUBLIC)? ID (COLON ID)? EQUALS compound_expression)
;

filterDeclaration:
	((PUBLIC)? ID (COLON ID)? EQUALS compound_expression_filter)
;

joinDeclaration:
	((PUBLIC)? ID (COLON ID)? EQUALS compound_expression_join)
;

declaration:
	DEC (
		LCB (
			simpleDeclaration
			| computedDeclaration
			| filterDeclaration
			| joinDeclaration
		)+ RCB
	| (simpleDeclaration | computedDeclaration | filterDeclaration)
	);

compound_expression_join
	:
		compound_expression_comparison JOIN compound_expression_comparison
	;

compound_expression_filter
	:
		ID FILTER compound_expression_comparison
	;

compound_expression_not
	:
		compound_expression_paren 
		|
		NEGATION compound_expression_comparison 
	;

compound_expression_comparison
	:
		compound_expression_not 
		(
			GTR compound_expression_mult_div 
			| LESS  compound_expression_mult_div
			| GTREQ compound_expression_mult_div 
			| LESSEQ compound_expression_mult_div 
			| EQUALITY compound_expression_mult_div 
		)*
	;

compound_expression_mult_div
	:
		compound_expression_comparison
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

compound_expression_paren
	:
		atom
		| LPAREN compound_expression RPAREN
	;

statement: compound_expression;

sync_block: SYNC LCB (statement)* RCB;

statements: (statement | sync_block)*;

component: COMPONENT ID LCB (declaration)* statements RCB;

repl_stmt: (import_statement)* (module | component | declaration)* statements;

module: MODULE ID LCB repl_stmt RCB ;