" vim:fdm=marker
"
" _____     _           ___ _             _         _           _              
"|_   _|  _| |___ _ _  / __| |_ __ _ _ __| |___ _ _( )___  __ _(_)_ __  _ _ __ 
"  | || || | / -_) '_| \__ \  _/ _` | '_ \ / -_) '_|/(_-<  \ V / | '  \| '_/ _|
"  |_| \_, |_\___|_|   |___/\__\__,_| .__/_\___|_|   /__/ (_)_/|_|_|_|_|_| \__|
"      |__/                         |_|                                        
"

" Set Options {{{
"Vim not vi
set nocompatible
set t_Co=256

"Change the shell to vanilla to support NeoBundle
set shell=/bin/bash

"Enable mouse usage for scrolling and resizing splits
set mouse+=a
if &term =~ '^screen'
  " tmux knows the extended mouse mode
  set ttymouse=xterm2
endif

"Set map leader
let mapleader=","

"Folding options
set foldnestmax=10
set foldmethod=indent

"Set the default encoding to fix windows bug where not all
"symbols are displayed by default.
set encoding=utf-8

"Help enforce 80 column code if available
if exists('colorcolumn')
  set colorcolum=80
else
  au BufWinEnter * let w:m2=matchadd('ErrorMsg', '\%>80v.\+', -1)
endif

"Show ex commands as they are being typed
set showcmd

"Use "Magic" aka regex during searches
set magic

"Set vim menu completion
set wildmenu
set wildmode=longest:list,full

"Show search results as typing
set incsearch
"Show line numbers
set number

"Show the status line even with just one window
set laststatus=2

"set omnifunc=syntaxcomplete#Complete

" }}}

" Mappings {{{

"Cycle through Quickfix list with F3 
map <F3> :cn<Enter>
map <S-F3> :cp<Enter>

"Change Buffers
map <leader>n :bn<Enter>
map <leader>p :bp<Enter>
map <leader>d :bd<Enter>

"When editing python F9 to drop to python shell
nnoremap <buffer> <F9> :exec '!python' shellescape(@%, 1)<cr>

"Mapping for Tagbar
nnoremap <leader>t :TagbarToggle<cr>

"Unite mappings
"Grep in current directory
nnoremap <leader>f :Unite -buffer-name=search -start-insert -auto-preview grep:.<CR>

"Fuzzy search like ctrl-p
nnoremap <C-P> :call Unite_ctrlp()<cr>

"File explorer like NerdTree
nnoremap <C-e> :VimFilerExplorer<cr>

" Plugin key-mappings.
imap <C-k>     <Plug>(neosnippet_expand_or_jump)
smap <C-k>     <Plug>(neosnippet_expand_or_jump)
xmap <C-k>     <Plug>(neosnippet_expand_target)

" SuperTab like snippets behavior.
"imap <expr><TAB>
"      \ pumvisible() ? "\<C-n>" :
"      \ neosnippet#expandable_or_jumpable() ?
"      \    "\<Plug>(neosnippet_expand_or_jump)" : "\<TAB>"
"smap <expr><TAB> neosnippet#expandable_or_jumpable() ?
"      \ "\<Plug>(neosnippet_expand_or_jump)" : "\<TAB>"

" <TAB>: completion.
inoremap <expr><TAB>  pumvisible() ? "\<C-n>" : "\<TAB>"
" Recommended key-mappings.

" Toggle Quick Preview
nnoremap  <leader>m :InstantMarkdownPreview<cr>

" Fix inconsisent Y behavior
nnoremap Y y$

" Vim Radical (Convert base)
nmap g<C-A> <Plug>RadicalView
xmap g<C-A> <Plug>RadicalView
nmap crd <Plug>RadicalCoerceToDecimal
nmap crx <Plug>RadicalCoerceToHex
nmap cro <Plug>RadicalCoerceToOctal
nmap crb <Plug>RadicalCoerceToBinary


" Set persistent_undo for undotree
if has("persistent_undo")
  set undodir=~/.undodir/
  set undofile
endif

" }}}

"Neobundle Config {{{

"Note: Skip initialization for vim-tiny or vim-small.
if 0 | endif

if has('vim_starting')
  if &compatible
    set nocompatible               " Be iMproved
  endif

  " Required:
  set runtimepath+=~/.vim/bundle/neobundle.vim/
endif

" Required:
call neobundle#begin(expand('~/.vim/bundle/'))

"NeoBundle Settings

" Let NeoBundle manage NeoBundle
" Required:
NeoBundleFetch 'Shougo/neobundle.vim'

NeoBundle 'Chiel92/vim-autoformat'
NeoBundle 'Shougo/neocomplete.vim.git'
NeoBundle 'Shougo/context_filetype.vim'
NeoBundle 'Shougo/neoinclude.vim'
NeoBundle 'Shougo/neosnippet'
NeoBundle 'Shougo/neosnippet-snippets'
NeoBundle 'honza/vim-snippets'
NeoBundle 'Shougo/neco-syntax'
NeoBundle 'Shougo/neopairs.vim'
NeoBundle 'Shougo/unite.vim'
NeoBundle 'vim-airline/vim-airline'
NeoBundle 'vim-airline/vim-airline-themes'
NeoBundle 'briancollins/vim-jst'
NeoBundle 'elzr/vim-json'
NeoBundle 'godlygeek/tabular'
NeoBundle 'groenewege/vim-less'
NeoBundle 'mattn/gist-vim'
NeoBundle 'tpope/vim-fugitive'
NeoBundle 'tpope/vim-surround'
NeoBundle 'tpope/vim-commentary'
NeoBundle 'flazz/vim-colorschemes'
NeoBundle 'Chiel92/vim-autoformat'
NeoBundle 'rking/ag.vim'
NeoBundle 'tapichu/asm2d-vim'
NeoBundle 'Shougo/vimfiler.vim'
NeoBundle 'Shougo/vimproc.vim', {
      \ 'build' : {
      \     'windows' : 'tools\\update-dll-mingw',
      \     'cygwin' : 'make -f make_cygwin.mak',
      \     'mac' : 'make',
      \     'linux' : 'make',
      \     'unix' : 'gmake',
      \    },
      \ }
NeoBundle 'Shougo/vimshell.vim'
NeoBundle 'Shougo/neossh.vim'
NeoBundle 'majutsushi/tagbar'
NeoBundle 'xolox/vim-misc'
"NeoBundle 'xolox/vim-easytags'
NeoBundle 'airblade/vim-gitgutter'
NeoBundle 'Cognoscan/vim-vhdl'
NeoBundle 'dbakker/vim-projectroot'
NeoBundle 'pangloss/vim-javascript'
NeoBundle 'avakhov/vim-yaml'
NeoBundle 'scrooloose/syntastic'
NeoBundle 'myint/syntastic-extras'
NeoBundle 'heavenshell/vim-pydocstring'
NeoBundle 'ternjs/tern_for_vim'
NeoBundle 'Raimondi/delimitMate'
NeoBundle 'pangloss/vim-javascript'
NeoBundle 'mattn/emmet-vim'
NeoBundle 'heavenshell/vim-jsdoc'
NeoBundle 'tpope/vim-repeat'
NeoBundle 'klen/python-mode'
NeoBundle 'dag/vim-fish'
NeoBundle 'plasticboy/vim-markdown'
NeoBundle 'dart-lang/dart-vim-plugin'
NeoBundle 'jceb/vim-hier'
NeoBundle 'dannyob/quickfixstatus'
NeoBundle 'Rip-Rip/clang_complete'
NeoBundle 'saltstack/salt-vim'
NeoBundle 'pearofducks/ansible-vim'
NeoBundle 'tpope/vim-dispatch'
NeoBundle 'tpope/vim-eunuch'
NeoBundle 'vim-scripts/bash-support.vim'
NeoBundle 'rhysd/vim-clang-format'
NeoBundle 'mbbill/undotree'
NeoBundle 'christoomey/vim-sort-motion'
NeoBundle 'lervag/vimtex'
NeoBundle 'idanarye/vim-vebugger'
NeoBundle 'ekalinin/Dockerfile.vim'
" Document utils
NeoBundle 'suan/vim-instant-markdown'
NeoBundle 'vim-pandoc/vim-pandoc'
NeoBundle 'vim-pandoc/vim-pandoc-syntax'
NeoBundle 'vim-pandoc/vim-pandoc-after'
NeoBundle 'tex/vimpreviewpandoc'
NeoBundle 'lambdalisue/vim-pandoc-preview'
NeoBundle 'mattn/webapi-vim'
NeoBundle 'LucHermitte/lh-vim-lib', {'name': 'lh-vim-lib'}
NeoBundle 'LucHermitte/local_vimrc', {'depends': 'lh-vim-lib'}
NeoBundle 'jacoborus/vim-jsdoc'
NeoBundle 'jamessan/vim-gnupg'
NeoBundle 'vim-scripts/DoxygenToolkit.vim'
NeoBundle 'fidian/hexmode'
NeoBundle 'google/vim-maktaba'
NeoBundle 'glts/vim-magnum'
NeoBundle 'glts/vim-radical', {'depends': 
      \ [ 
      \   'google/vim-maktaba',
      \   'glts/vim-magnum'
      \ ]}
NeoBundle 'christoomey/vim-titlecase'
NeoBundle 'fadein/FIGlet.vim'
call neobundle#end()

filetype plugin indent on
" If there are uninstalled bundles found on
"startup,
" this will conveniently prompt you to
"install them.
NeoBundleCheck

" }}}

" Autocommands {{{

"Makefile filetype
au FileType make setlocal noexpandtab

"Python filetype
au FileType python setlocal tabstop=4 shiftwidth=4 softtabstop=4 expandtab

"Javascript filetype
au FileType javascript setlocal omnifunc=tern#Complete tabstop=2 shiftwidth=2 softtabstop=2 expandtab

"vim autocmd
au FileType vim setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab

"Yaml filetype 
au FileType yml setlocal indentkeys-=<:> tabstop=2 softtabstop=2 expandtab

"fish filetype 
au Filetype fish compiler fish setlocal textwidth=79  foldmethod=expr

"C filetype
au FileType c setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab

"Dart filetype
augroup dart
au FileType dart setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab
"autocmd FileType dart inoremap {<cr> {<cr>}<c-o>O<tab>
"autocmd FileType dart inoremap [<cr> [<cr>]<c-o>O<tab>
"autocmd FileType dart inoremap (<cr> (<cr>)<c-o>O<tab>)]}
augroup END

"Markdown filetype
augroup markdown
  au! FileType,BufRead,BufNewFile *.markdown set filetype=mkd spell
  au! FileType,BufRead,BufNewFile *.md       set filetype=mkd spell
augroup END

"Pandoc
augroup pandoc
  au Filetype pandoc let loaded_delimitMate = 1
  au Filetype pandoc NeoCompleteLock
  au Filetype pandoc :DelimitMateSwitch
augroup END

"html
au FileType html setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab

" }}}

" Plugin Configuration {{{

" Unite Vim
call unite#filters#matcher_default#use(['matcher_fuzzy'])
call unite#filters#sorter_default#use(['sorter_rank'])
call unite#custom#source('file,file/new,buffer,te -buffer-name=search -start-insert -auto-preview grep -custom-grep-command file_rec,line', 'matchers', 'matcher_fuzzy')

" Build the ctrlp function, using projectroot to define the 
" working directory.
function! Unite_ctrlp()
  execute ':Unite  -buffer-name=files -start-insert -match-input buffer file_rec/async'
endfunction


"Select Search
if executable('Ag')
  " Use ag (the silver searcher)
  " https://github.com/ggreer/the_silver_searcher
  let g:unite_source_grep_command = 'Ag'
  let g:unite_source_grep_default_opts =
        \ '-i --hidden --ignore ' .
        \ '''.hg'' --ignore ''.svn'' --ignore ''.git'' --ignore ''.bzr'''
  let g:unite_source_grep_recursive_opt = ''
elseif executable('ack-grep')
  " Use ack
  " http://beyondgrep.com/
  let g:unite_source_grep_command = 'ack-grep'
  let g:unite_source_grep_default_opts = '-i --no-heading --no-color -k -H'
  let g:unite_source_grep_recursive_opt = ''
endif

" Enable file operation commands.
" Edit file by tabedit.
call vimfiler#custom#profile('default', 'context', {
      \ 'safe' : 0
      \ })

" Like Textmate icons.
let g:vimfiler_tree_leaf_icon = ' '
let g:vimfiler_tree_opened_icon = '▾'
let g:vimfiler_tree_closed_icon = '▸'
let g:vimfiler_file_icon = '-'
let g:vimfiler_marked_file_icon = '*'

" Unite Options
let g:unite_source_history_yank_enable=1
let g:unite_enable_start_insert=1
let g:unite_ignore_source_files = [ 'packages' ]

let g:vimfiler_as_default_explorer = 1


"Neocomplete config
let g:neocomplete#enable_at_startup = 1
let g:neocomplete#enable_auto_select = 0
let g:neocomplcache_enable_at_startup = 0
let g:neocomplete#use_vimproc = 1

if !exists('g:neocomplete#force_omni_input_patterns')
  let g:neocomplete#force_omni_input_patterns = {}
endif
let g:neocomplete#force_omni_input_patterns.c =
      \ '[^.[:digit:] *\t]\%(\.\|->\)\w*'
let g:neocomplete#force_omni_input_patterns.cpp =
      \ '[^.[:digit:] *\t]\%(\.\|->\)\w*\|\h\w*::\w*'
let g:neocomplete#force_omni_input_patterns.objc =
      \ '\[\h\w*\s\h\?\|\h\w*\%(\.\|->\)'
let g:neocomplete#force_omni_input_patterns.objcpp =
      \ '\[\h\w*\s\h\?\|\h\w*\%(\.\|->\)\|\h\w*::\w*'
let g:clang_complete_auto = 0
let g:clang_auto_select = 0
let g:clang_omnicppcomplete_compliance = 0
let g:clang_make_default_keymappings = 0
"let g:clang_use_library = 1

if !exists('g:neocomplete#force_omni_input_patterns')
  let g:neocomplete#force_omni_input_patterns = {}
endif
let g:neocomplete#force_omni_input_patterns.tex =
      \ '\v\\%('
      \ . '\a*cite\a*%(\s*\[[^]]*\]){0,2}\s*\{[^}]*'
      \ . '|\a*ref%(\s*\{[^}]*|range\s*\{[^,}]*%(}\{)?)'
      \ . '|includegraphics\*?%(\s*\[[^]]*\]){0,2}\s*\{[^}]*'
      \ . '|%(include%(only)?|input)\s*\{[^}]*'
      \ . ')'


"Airline Config
let g:airline#extensions#tabline#enabled = 1
let g:airline#extensions#virtualenv#enabled = 1

if !exists('g:airline_symbols')
  let g:airline_symbols = {}
endif

let g:airline_left_sep = '▶'
let g:airline_right_sep = '«'

"Colorscheme
colorscheme badwolf
let g:airline_theme = 'badwolf'

"Ag vim settings
let g:ag_working_path_mode='r'

"Syntastic settings
set statusline+=%#warningmsg#
set statusline+=%{SyntasticStatuslineFlag()}
set statusline+=%*

let g:syntastic_always_populate_loc_list = 1
let g:syntastic_auto_loc_list = 2
let g:syntastic_check_on_open = 0
let g:syntastic_check_on_wq = 0
let g:syntastic_aggregate_errors = 1
let g:syntastic_error_symbol = "✗"
let g:syntastic_id_checkers = 1
let g:syntastic_auto_jump = 0
let g:syntastic_quiet_messages = { "level": "warnings" }

let g:syntastic_text_checkers = ['language_check']
let g:syntastic_language_check_args = '--language=en-US'

let g:syntastic_mode_map = { "mode": "active",
      \ "passive_filetypes": ["dart"] }

"Syntastic Extras Settings
let g:syntastic_make_checkers = ['gnumake']
let g:syntastic_javascript_checkers = ['json_tool']
let g:syntastic_yaml_checkers = ['pyyaml']
let g:syntastic_gitcommit_checkers = ['language_check']
let g:syntastic_svn_checkers = ['language_check']

"Tagbar settings
let g:tagbar_type_vimwiki = {
      \ 'ctagstype' : 'wiki',
      \ 'kinds'     : [
      \ 'h:headers'
      \ ]
      \ }
let g:tagbar_type_mkd= {
      \ 'ctagstype' : 'md',
      \ 'kinds' : [
      \ 'h:headings'
      \ ],
      \ 'sort' : 0,
      \ }
let g:tagbar_type_css= {
      \ 'ctagstype' : 'css',
      \ 'kinds' : [
      \ 'c:classes',
      \ 'i:ids',
      \ 't:tags',
      \ 'm:media',
      \ 'f:fonts',
      \ 'k:keyframes'
      \ ],
      \ 'sort' : 0,
      \ }
let g:tagbar_type_html= {
      \ 'ctagstype' : 'html',
      \ 'kinds'     : [
      \ 'i:ids',
      \ 'c:classes',
      \ ]
      \ }
let g:tagbar_type_vhdl = {
      \ 'ctagstype': 'vhdl',
      \ 'kinds' : [
      \'d:prototypes',
      \'b:package bodies',
      \'e:entities',
      \'a:architectures',
      \'t:types',
      \'p:processes',
      \'f:functions',
      \'r:procedures',
      \'c:constants',
      \'T:subtypes',
      \'r:records',
      \'C:components',
      \'P:packages',
      \'l:locals'
      \]
      \}
let g:gitgutter_max_signs = 1000

"EasyTags settings
let g:easytags_auto_update = 1
let g:easytags_on_cursorhold = 0
let g:easytags_async = 1
let g:easytags_resolve_links = 1

"Vim-Javascript settings
let g:javascript_enable_domhtmlcss = 1

"clang-format options
let g:clang_format#style_options = {
      \ "AccessModifierOffset" : -2,
      \ "AllowShortIfStatementsOnASingleLine" : "true",
      \ "AlwaysBreakTemplateDeclarations" : "true",
      \ "Standard" : "Auto",
      \ "BreakBeforeBraces" : "GNU"}


" For conceal markers.
"if has('conceal')
"  set conceallevel=2 concealcursor=niv
"endif

"Neosnippet options
let g:neosnippet#snippets_directory='~/.vimsnippets'

"Instant Markdown options
let g:instant_markdown_autostart = 0

"Pandoc 
let g:pandoc#syntax#conceal#use = 0
let g:pandoc#syntax#conceal#blacklist = ["block", "codeblock_start", "codeblock_delim"]
let g:pandoc#formatting#mode = "ha"
let g:pandoc#formatting#smart_autoformat_on_cursormoved = 1
let g:pandoc#folding#level = 2
let g:pandoc#folding#mode = "relative"
let g:pandoc#after#modules#enabled = ["nrrwrgn", "tablemode", "unite"]
let g:pandoc#completion#bib#mode = 'citeproc'
let g:pandoc#syntax#colorcolumn = 1

"Emmet settings
let g:user_emmet_leader_key='<leader>e'

"JsDoc settings
let g:jsdoc_allow_input_prompt = 1

augroup myvimrc
  au!
  au BufWritePost .vimrc,_vimrc,vimrc,.gvimrc,_gvimrc,gvimrc so $MYVIMRC | if has('gui_running') | so $MYGVIMRC | endif
  augroup END
"}}}
