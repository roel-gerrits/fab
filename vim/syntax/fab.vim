" Vim syntax file for fab build files (see fab/lang/grammar.lark)
if exists("b:current_syntax")
  finish
endif

syn case match

syn keyword fabKeyword for in
syn region fabComment start=/#/ end=/$/
syn region fabString start=/"/ skip=/\\./ end=/"/

syn match fabBuiltin /\<\(load\|path\|link\|http_get\|extract\|http_archive\|gcc_compile\|gcc_link\|gcc_collect_compile_commands\|containerized_gcc\)\>/
syn match fabFunc /\<[A-Za-z_][A-Za-z0-9_]*\ze\s*(/
syn match fabAssign /^\s*[A-Za-z_][A-Za-z0-9_]*\ze\s*=/

hi def link fabKeyword Keyword
hi def link fabComment Comment
hi def link fabString String
hi def link fabBuiltin Function
hi def link fabFunc Function
hi def link fabAssign Identifier

let b:current_syntax = "fab"
