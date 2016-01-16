"
"Tyler Stapler's vimrc file
"
"author: Tyler Stapler
"

"Vim not vi
set nocompatible
set t_Co=256

"Change the shell from fish to support NeoBundle
set shell=/bin/sh

"Set map leader
let mapleader=","

"Folding options
set foldnestmax=10
set foldmethod=indent

"Set the default encoding to fix windows bug where not all
"symbols are displayed by default.
set encoding=utf-8

"Mappings 

"Use the space bar to open/close folds
nnoremap <space> za

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

"Mappings for Eclim
nnoremap <silent> <buffer> <leader>i :JavaImport<cr>
nnoremap <silent> <buffer> <leader>d :JavaDocSearch -x declarations<cr>
nnoremap <silent> <buffer> <cr> :JavaSearchContext<cr>

"Unite mappings
nnoremap <leader>f :Unite -buffer-name=search -start-insert -auto-preview grep:.<CR>
nnoremap <space>y :Unite history/yank<cr>

"File explorer like NerdTree
nnoremap <C-e> :VimFilerExplorer<cr>

"Neosnippet Settings
" Plugin key-mappings.
imap <C-k>     <Plug>(neosnippet_expand_or_jump)
smap <C-k>     <Plug>(neosnippet_expand_or_jump)
xmap <C-k>     <Plug>(neosnippet_expand_target)

" SuperTab like snippets behavior.
imap <expr><TAB>
			\ pumvisible() ? "\<C-n>" :
			\ neosnippet#expandable_or_jumpable() ?
			\    "\<Plug>(neosnippet_expand_or_jump)" : "\<TAB>"
smap <expr><TAB> neosnippet#expandable_or_jumpable() ?
			\ "\<Plug>(neosnippet_expand_or_jump)" : "\<TAB>"

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

"Vim master race

"Show search results as typing
set incsearch
"Show line numbers
set number

"Show the status line even with just one window
set laststatus=2

"Enable YouCompleteMe"
filetype plugin indent on

"Yaml filetype commands
au FileType yml setl indentkeys-=<:> tabstop=2 softtabstop=2 expandtab

set omnifunc=syntaxcomplete#Complete



"Neobundle Config
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

" Let NeoBundle manage NeoBundle
" Required:
NeoBundleFetch 'Shougo/neobundle.vim'

" My Bundles here:
" Refer to |:NeoBundle-examples|.
" Note: You don't set neobundle setting in
".gvimrc!
"
NeoBundle 'Chiel92/vim-autoformat'
NeoBundle 'Shougo/neocomplete.vim.git'
NeoBundle 'Shougo/context_filetype.vim'
NeoBundle 'Shougo/neoinclude.vim'
NeoBundle 'Shougo/neosnippet'
NeoBundle 'Shougo/neosnippet-snippets'
NeoBundle 'Shougo/neco-syntax'
NeoBundle 'Shougo/neopairs.vim'
NeoBundle 'Shougo/unite.vim'
NeoBundle 'bling/vim-airline'
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
NeoBundle 'dansomething/vim-eclim'
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
NeoBundle 'xolox/vim-easytags'
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
NeoBundle 'xolox/vim-session'

call neobundle#end()

filetype plugin indent on
" If there are uninstalled bundles found on
"startup,
" this will conveniently prompt you to
"install them.
NeoBundleCheck

"Makefile autocmd
autocmd FileType make setlocal noexpandtab

"Python autocmd
autocmd FileType python setlocal tabstop=4 shiftwidth=4 softtabstop=4 expandtab

"Javascript autocmd
autocmd FileType javascript setlocal omnifunc=tern#Complete

"vim autocmd
autocmd FileType vim setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab


"Unite Vim
call unite#filters#matcher_default#use(['matcher_fuzzy'])
call unite#filters#sorter_default#use(['sorter_rank'])
call unite#custom#source('file,file/new,buffer,te -buffer-name=search -start-insert -auto-preview grep -custom-grep-command file_rec,line', 'matchers', 'matcher_fuzzy')

" Build the ctrlp function, using projectroot to define the 
" working directory.
function! Unite_ctrlp()
	execute ':Unite  -buffer-name=files -start-insert -match-input buffer file_rec/async:'.ProjectRootGuess().'/'
endfunction

"Fuzzy search like ctrl-p
nnoremap <C-P> :call Unite_ctrlp()<cr>

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
	let g:unite_source_grep_default_opts =
				\ '-i --no-heading --no-color -k -H'
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

let g:unite_source_history_yank_enable=1
let g:unite_enable_start_insert=1

let g:vimfiler_as_default_explorer = 1

"Neocomplete config
let g:neocomplete#enable_at_startup = 1
let g:neocomplete#enable_auto_select = 0
let g:neocomplcache_enable_at_startup = 0
let g:neocomplete#use_vimproc = 1

" <TAB>: completion.
inoremap <expr><TAB>  pumvisible() ? "\<C-n>" : "\<TAB>"
" Recommended key-mappings.

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
let g:syntastic_auto_jump = 3
let g:syntastic_quiet_messages = { "level": "warnings" }

let g:syntastic_text_checkers = ['language_check']
let g:syntastic_language_check_args = '--language=en-US'

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

"Easytags Settings
let g:easytags_async = 1

"Eclim settings
let g:EclimFileTypeValidate = 0

"EasyTags settings
let g:easytags_async = 1
let g:easytags_always_enabled = 1

"Vim-Javascript settings
let g:javascript_enable_domhtmlcss = 1

"Vim-Session
let g:session_autosave='no'

" For conceal markers.
if has('conceal')
	set conceallevel=2 concealcursor=niv
endif

"Auto Refresh Config if updated
augroup myvimrc
	au!
	au BufWritePost .vimrc,_vimrc,vimrc,.gvimrc,_gvimrc,gvimrc,.vimrc.local,.vimrc.bundle.local so $MYVIMRC | if has('gui_running') | so $MYGVIMRC | endif
	augroup END
