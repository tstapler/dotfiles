;;; evil-tabs-autoloads.el --- automatically extracted autoloads
;;
;;; Code:


;;;### (autoloads (global-evil-tabs-mode turn-off-evil-tabs-mode
;;;;;;  turn-on-evil-tabs-mode evil-tabs-mode) "evil-tabs" "evil-tabs.el"
;;;;;;  (21952 55945 493481 999000))
;;; Generated autoloads from evil-tabs.el

(defvar evil-tabs-mode nil "\
Non-nil if Evil-Tabs mode is enabled.
See the command `evil-tabs-mode' for a description of this minor mode.
Setting this variable directly does not take effect;
either customize it (see the info node `Easy Customization')
or call the function `evil-tabs-mode'.")

(custom-autoload 'evil-tabs-mode "evil-tabs" nil)

(autoload 'evil-tabs-mode "evil-tabs" "\
Integrating Vim-style tabs for Evil mode users.

\(fn &optional ARG)" t nil)

(autoload 'turn-on-evil-tabs-mode "evil-tabs" "\
Enable `evil-tabs-mode' in the current buffer.

\(fn)" nil nil)

(autoload 'turn-off-evil-tabs-mode "evil-tabs" "\
Disable `evil-tabs-mode' in the current buffer.

\(fn)" nil nil)

(defvar global-evil-tabs-mode nil "\
Non-nil if Global-Evil-Tabs mode is enabled.
See the command `global-evil-tabs-mode' for a description of this minor mode.
Setting this variable directly does not take effect;
either customize it (see the info node `Easy Customization')
or call the function `global-evil-tabs-mode'.")

(custom-autoload 'global-evil-tabs-mode "evil-tabs" nil)

(autoload 'global-evil-tabs-mode "evil-tabs" "\
Toggle Evil-Tabs mode in all buffers.
With prefix ARG, enable Global-Evil-Tabs mode if ARG is positive;
otherwise, disable it.  If called from Lisp, enable the mode if
ARG is omitted or nil.

Evil-Tabs mode is enabled in all buffers where
`turn-on-evil-tabs-mode' would do it.
See `evil-tabs-mode' for more information on Evil-Tabs mode.

\(fn &optional ARG)" t nil)

;;;***

;;;### (autoloads nil nil ("evil-tabs-pkg.el") (21952 55945 499909
;;;;;;  609000))

;;;***

(provide 'evil-tabs-autoloads)
;; Local Variables:
;; version-control: never
;; no-byte-compile: t
;; no-update-autoloads: t
;; coding: utf-8
;; End:
;;; evil-tabs-autoloads.el ends here
