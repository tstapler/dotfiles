;;; ctags-update-autoloads.el --- automatically extracted autoloads
;;
;;; Code:


;;;### (autoloads (turn-on-ctags-auto-update-mode ctags-auto-update-mode
;;;;;;  ctags-update) "ctags-update" "ctags-update.el" (21952 56790
;;;;;;  996022 0))
;;; Generated autoloads from ctags-update.el

(autoload 'ctags-update "ctags-update" "\
update TAGS in parent directory using `exuberant-ctags' you
can call this function directly , or enable
`ctags-auto-update-mode' or with prefix `C-u' then you can
generate a new TAGS file in directory

\(fn &optional ARGS)" t nil)

(autoload 'ctags-auto-update-mode "ctags-update" "\
auto update TAGS using `exuberant-ctags' in parent directory.

\(fn &optional ARG)" t nil)

(autoload 'turn-on-ctags-auto-update-mode "ctags-update" "\
turn on `ctags-auto-update-mode'.

\(fn)" t nil)

;;;***

;;;### (autoloads nil nil ("ctags-update-pkg.el") (21952 56791 5406
;;;;;;  179000))

;;;***

(provide 'ctags-update-autoloads)
;; Local Variables:
;; version-control: never
;; no-byte-compile: t
;; no-update-autoloads: t
;; coding: utf-8
;; End:
;;; ctags-update-autoloads.el ends here
