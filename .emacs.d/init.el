;; packages
(setq package-archives '(("gnu" . "http://elpa.gnu.org/packages/")
                         ("org" . "http://orgmode.org/elpa/")
                        ("marmalade" . "http://marmalade-repo.org/packages/")
                         ("melpa-stable" . "http://melpa-stable.milkbox.net/packages/")))
(package-initialize)

(defun require-package (package)
  (setq-default highlight-tabs t)
  "Install given PACKAGE."
  (unless (package-installed-p package)
    (unless (assoc package package-archive-contents)
      (package-refresh-contents))
    (package-install package)))

(require `evil)
(evil-mode 1)

(setq scroll-margin 5
scroll-conservatively 9999
scroll-step 1)

(color-theme-approximate-on)

(helm-mode 1)
(define-key evil-normal-state-map " " `helm-mini)
(global-set-key (kbd "M-x") 'helm-M-x)

(require `powerline)
(powerline-evil-vim-color-theme)
(display-time-mode t)
