;;; eaf-video-player.el --- Video player

;; Filename: eaf-video-player.el
;; Description: Video player
;; Author: Andy Stewart <lazycat.manatee@gmail.com>
;; Maintainer: Andy Stewart <lazycat.manatee@gmail.com>
;; Copyright (C) 2021, Andy Stewart, all rights reserved.
;; Created: 2021-07-31 20:41:48
;; Version: 0.1
;; Last-Updated: 2021-07-31 20:41:48
;;           By: Andy Stewart
;; URL: http://www.emacswiki.org/emacs/download/eaf-video-player.el
;; Keywords:
;; Compatibility: GNU Emacs 28.0.50
;;
;; Features that might be required by this library:
;;
;;
;;

;;; This file is NOT part of GNU Emacs

;;; License
;;
;; This program is free software; you can redistribute it and/or modify
;; it under the terms of the GNU General Public License as published by
;; the Free Software Foundation; either version 3, or (at your option)
;; any later version.

;; This program is distributed in the hope that it will be useful,
;; but WITHOUT ANY WARRANTY; without even the implied warranty of
;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;; GNU General Public License for more details.

;; You should have received a copy of the GNU General Public License
;; along with this program; see the file COPYING.  If not, write to
;; the Free Software Foundation, Inc., 51 Franklin Street, Fifth
;; Floor, Boston, MA 02110-1301, USA.

;;; Commentary:
;;
;; Video player
;;

;;; Installation:
;;
;; Put eaf-video-player.el to your load-path.
;; The load-path is usually ~/elisp/.
;; It's set in your ~/.emacs like this:
;; (add-to-list 'load-path (expand-file-name "~/elisp"))
;;
;; And the following to your ~/.emacs startup file.
;;
;; (require 'eaf-video-player)
;;
;; No need more.

;;; Customize:
;;
;;
;;
;; All of the above can customize by:
;;      M-x customize-group RET eaf-video-player RET
;;

;;; Change log:
;;
;; 2021/07/31
;;      * First released.
;;

;;; Acknowledgements:
;;
;;
;;

;;; TODO
;;
;;
;;

;;; Require

;;; Code:

(defcustom eaf-video-player-keybinding
  '(("SPC" . "toggle_play")
    ("x" . "close_buffer")
    ("h" . "play_backward")
    ("l" . "play_forward")
    ("j" . "decrease_volume")
    ("k" . "increase_volume")
    ("f" . "toggle_fullscreen")
    ("r" . "restart")
    ("s" . "subtitle"))

  "The keybinding of EAF Video Player."
  :type 'cons)

(setq eaf-video-player-keybinding
      '(("SPC" . "toggle_play")
        ("x" . "close_buffer")
        ("h" . "play_backward")
        ("l" . "play_forward")
        ("[" . "decrease_volume")
        ("]" . "increase_volume")
        ("j" . "play_backward_subtitle")
        ("k" . "play_forward_subtitle")
        ("f" . "toggle_fullscreen")
        ("d" . "download_subtitles")
        ("s" . "reload_subtitles")
        ("r" . "restart")))


(defcustom eaf-video-extension-list
  '("avi" "webm" "rmvb" "ogg" "mp4" "mkv" "m4v")
  "The extension list of video player application."
  :type 'cons)

(defun eaf-video-player--navigate-by-subtitles (&rest subtitles)
  (print subtitles)
  (completing-read "navigate by subtitles: " subtitles))

(add-to-list 'eaf-app-binding-alist '("video-player" . eaf-video-player-keybinding))

(setq eaf-video-player-module-path (concat (file-name-directory load-file-name) "buffer.py"))
(add-to-list 'eaf-app-module-path-alist '("video-player" . eaf-video-player-module-path))

(add-to-list 'eaf-app-extensions-alist '("video-player" . eaf-video-extension-list))

(defun eaf-video-player-lookup (text x y)
  (eaf-call-async "execute_function_with_args" eaf--buffer-id "message_box_update" text x y))

(defun eaf-video-player-explain-sentence (text x y)
  (eaf-call-async "execute_function_with_args" eaf--buffer-id "message_box_update" text x y))


(provide 'eaf-video-player)

;;; eaf-video-player.el ends here
