;;; politics.lisp — мозг политики Юсиксландии 🫠🗳
;;; читает politics.json (данные из politics.py), считает всё сам:
;;;   расстояния между позициями, поддержку партий, лидера партии.
;;; запуск: sbcl --script politics.lisp [команда]
;;;   (нет)/show       — политическая карта с поддержкой
;;;   axes             — список осей
;;;   rate             — поддержка партий (текстом)
;;;   rate --json      — поддержка машинно (JSON в stdout, всё прочее в stderr)
;;;   closest <id>     — какой партии ближе гражданин (с раскладом по осям)
;;;   leader <party>   — кого партия выдвинула бы лидером
;;;   distances        — матрица «гражданин × партия»

(defpackage :politics (:use :cl))
(in-package :politics)

(defparameter *base* (make-pathname :name nil :type nil :defaults *load-pathname*))
(defparameter *politics-file* (merge-pathnames "politics.json" *base*))
(defparameter *json-out* nil "когда T — человеческий вывод уходит в stderr, в stdout только JSON")
(defparameter *q* (string (code-char 34)) "кавычка — как символ, чтобы не путать лисп-ридер")
(defparameter *bs* (string (code-char 92)) "обратный слэш — то же самое")

;; ────────────────────────────── мини-JSON

(defun skip-ws (s i)
  (loop while (and (< i (length s)) (find (char s i) '(#\Space #\Tab #\Newline #\Return)))
        do (incf i))
  i)

(defun parse-hex4 (s i)
  (let ((n 0))
    (dotimes (k 4)
      (setf n (+ (* n 16) (digit-char-p (char s (+ i k)) 16))))
    (values n (+ i 4))))

(defun parse-json-string (s i)
  "i указывает на открывающую кавычку. → (values строка новая-позиция)"
  (let ((out (make-string-output-stream))
        (q (char *q* 0))
        (bs (char *bs* 0))
        (i (1+ i)))
    (loop
      (let ((ch (char s i)))
        (cond
          ((char= ch q) (return (values (get-output-stream-string out) (1+ i))))
          ((char= ch bs)
           (let ((esc (char s (1+ i))))
             (cond
               ((char= esc q) (write-char q out) (incf i 2))
               ((char= esc bs) (write-char bs out) (incf i 2))
               ((char= esc #\/) (write-char #\/ out) (incf i 2))
               ((char= esc #\b) (write-char #\Backspace out) (incf i 2))
               ((char= esc #\f) (write-char #\Page out) (incf i 2))
               ((char= esc #\n) (write-char #\Newline out) (incf i 2))
               ((char= esc #\r) (write-char #\Return out) (incf i 2))
               ((char= esc #\t) (write-char #\Tab out) (incf i 2))
               ((char= esc #\u) (multiple-value-bind (code next) (parse-hex4 s (+ i 2))
                                   (write-char (code-char code) out)
                                   (setf i next)))
               (t (write-char esc out) (incf i 2)))))
          (t (write-char ch out) (incf i)))))))

(defun parse-json-number (s i)
  (let ((start i))
    (loop while (and (< i (length s))
                     (or (digit-char-p (char s i))
                         (find (char s i) '(#\- #\+ #\. #\e #\E))))
          do (incf i))
    (values (read-from-string (subseq s start i)) i)))

(defun parse-json-array (s i)
  (let ((items '())
        (i (skip-ws s (1+ i))))
    (if (char= (char s i) #\])
        (values (nreverse items) (1+ i))
        (loop
          (multiple-value-bind (val next) (parse-json-value s i)
            (push val items)
            (setf i (skip-ws s next)))
          (if (char= (char s i) #\,)
              (setf i (skip-ws s (1+ i)))
              (return (values (nreverse items) (1+ i))))))))

(defun parse-json-object (s i)
  (let ((table (make-hash-table :test #'equal))
        (i (skip-ws s (1+ i))))
    (if (char= (char s i) #\})
        (values table (1+ i))
        (loop
          (setf i (skip-ws s i))
          (multiple-value-bind (key next) (parse-json-string s i)
            (setf i (skip-ws s next))
            (setf i (skip-ws s (1+ i)))  ; двоеточие
            (multiple-value-bind (val after) (parse-json-value s i)
              (setf (gethash key table) val)
              (setf i (skip-ws s after))))
          (if (char= (char s i) #\,)
              (setf i (skip-ws s (1+ i)))
              (return (values table (1+ i))))))))

(defun parse-json-value (s i)
  (let* ((i (skip-ws s i))
         (ch (char s i))
         (q (char *q* 0)))
    (cond
      ((char= ch #\{) (parse-json-object s i))
      ((char= ch #\[) (parse-json-array s i))
      ((char= ch q) (parse-json-string s i))
      ((char= ch #\t) (values t (+ i 4)))
      ((char= ch #\f) (values nil (+ i 5)))
      ((char= ch #\n) (values nil (+ i 4)))
      (t (parse-json-number s i)))))

(defun load-json (path)
  (with-open-file (s path :direction :input :external-format :utf-8)
    (let ((text (make-string (file-length s))))
      (subseq text 0 (read-sequence text s))
      (multiple-value-bind (val pos) (parse-json-value text 0)
        (declare (ignore pos))
        val))))

;; ────────────────────────────── данные

(defun g (table key &optional default)
  (if (hash-table-p table) (gethash key table default) default))

(defun num (x &optional (default 0.0))
  (if (numberp x) (float x 1.0) default))

(defvar *politics* nil)
(defvar *axes* nil)

(defun load-politics ()
  (unless *politics*
    (unless (probe-file *politics-file*)
      (format *error-output* "❌ нет politics.json — сначала: python3 politics.py init~%")
      (sb-ext:exit :code 1))
    (setf *politics* (load-json *politics-file*))
    (setf *axes* (mapcar (lambda (a) (g a "id")) (g *politics* "axes"))))
  *politics*)

(defun axis-ids () (load-politics) *axes*)

(defun party-list () (g (load-politics) "parties"))
(defun citizen-list () (g (load-politics) "citizens"))

(defun pos-of (obj) (g obj "pos"))

(defun axis-val (pos axis)
  (num (g pos axis)))

(defun pos-distance (p1 p2)
  "евклидово расстояние между двумя позициями (по всем осям)"
  (let ((sum 0.0))
    (dolist (ax (axis-ids))
      (let ((d (- (axis-val p1 ax) (axis-val p2 ax))))
        (incf sum (* d d))))
    (sqrt sum)))

(defparameter *dmax* 4.0 "максимум: 4 оси × разброс 2")

;; ────────────────────────────── расчёты

(defun support-weight (citizen party)
  "вес голоса гражданина за партию: близость² × (лояльность + бонус за явку)"
  (let* ((d (pos-distance (pos-of citizen) (pos-of party)))
         (raw (max 0.0 (- 1.0 (/ d *dmax*))))
         (loyalty (num (g citizen "loyalty") 0.5))
         (declared (or (g citizen "party") (g citizen "declared_party")))
         (bonus (if (and declared (equal declared (g party "id"))) 0.35 0.0)))
    (+ (* raw raw (+ 0.45 (* 0.55 loyalty))) bonus)))

(defun support (party)
  (let ((sum 0.0))
    (dolist (c (citizen-list)) (incf sum (support-weight c party)))
    sum))

(defun support-table ()
  "список (партия . вес) плюс нормализованные доли"
  (let* ((parties (party-list))
         (raw (mapcar (lambda (pt) (cons pt (support pt))) parties))
         (total (reduce #'+ raw :key #'cdr :initial-value 0.0)))
    (values
     (mapcar (lambda (pair)
               (list (car pair) (cdr pair)
                     (if (> total 0) (* 100.0 (/ (cdr pair) total)) 0.0)))
             raw)
     total)))

(defun party-leader (party)
  "самый близкий гражданин к партии — он и есть лидер"
  (let ((best nil) (best-w -1.0))
    (dolist (c (citizen-list))
      (let ((w (support-weight c party)))
        (when (> w best-w) (setf best-w w best c))))
    (values best best-w)))

(defun party-by-id (id)
  (find id (party-list) :key (lambda (pt) (g pt "id")) :test #'equal))

(defun support-rows () (car (multiple-value-list (support-table))))

(defun unique-leaders ()
  "жадное назначение: партии по поддержке, каждый гражданин — лидер максимум одной"
  (let ((taken '()) (res '()))
    (dolist (row (sort (copy-list (support-rows)) #'> :key #'second))
      (destructuring-bind (party weight share) row
        (declare (ignore weight share))
        (let ((cand nil) (best -1.0))
          (dolist (c (citizen-list))
            (let ((w (support-weight c party)))
              (when (and (> w best) (not (member (g c "id") taken :test #'equal)))
                (setf best w cand c))))
          (when cand
            (push (g cand "id") taken)
            (push (cons (g party "id") cand) res)))))
    (nreverse res)))

(defun nearest-party (citizen)
  "ближайшая партия гражданина → (values party-id расстояние)"
  (let ((best nil) (best-d 99.0))
    (dolist (pt (party-list))
      (let ((d (pos-distance (pos-of citizen) (pos-of pt))))
        (when (< d best-d) (setf best-d d best pt))))
    (values (and best (g best "id")) best-d)))

(defun fmt (x &optional (digits 2))
  (format nil (format nil "~~,~DF" digits) x))

;; ────────────────────────────── вывод

(defun print-axes ()
  (format t "~%━━━ ОСИ ~A ━━━~%" (g (load-politics) "state"))
  (dolist (a (g (load-politics) "axes"))
    (format t "  ~A (~A): ~A ↔ ~A — ~A~%"
            (g a "name") (g a "id") (g a "left") (g a "right") (g a "question"))))

(defun print-rate ()
  (multiple-value-bind (rows total) (support-table)
    (format t "~%━━━ ПОДДЕРЖКА ПАРТИЙ (расчёт лиспа) ━━━~%")
    (format t "электорат: ~D граждан · суммарный вес: ~A~%" (length (citizen-list)) (fmt total))
    (dolist (row (sort (copy-list rows) #'> :key #'third))
      (destructuring-bind (party weight share) row
        (let ((bar (make-string (max 0 (round (/ share 4))) :initial-element #\█)))
          (format t "  ~A~A~%    «~A»: ~A вес, ~A%~%"
                  bar " " (g party "name") (fmt weight) (fmt share 1)))))))

(defun print-json-rate ()
  "машинный вывод: только JSON в stdout (человеческий вывод лиспа идёт в stderr)"
  (multiple-value-bind (rows total) (support-table)
    (declare (ignore total))
    (let ((out (make-string-output-stream)))
      (format out "{~A~A~A:~A" *q* "support" *q* "{")
      (loop for row in rows
            for first = t then nil
            do (unless first (format out ","))
               (format out "~S:~A" (g (first row) "id") (fmt (third row) 1)))
      (format out "},~A~A~A:~A" *q* "leader" *q* "{")
      (loop for pair in (unique-leaders)
            for first = t then nil
            do (unless first (format out ","))
               (format out "~S:~S" (car pair) (g (cdr pair) "name")))
      (format out "},~A~A~A:~A" *q* "nearest" *q* "{")
      (loop for c in (citizen-list)
            for first = t then nil
            do (unless first (format out ","))
               (multiple-value-bind (pid d) (nearest-party c)
                 (declare (ignore d))
                 (if pid
                     (format out "~S:~S" (g c "id") pid)
                     (format out "~S:null" (g c "id")))))
      (format out "}}")
      (format t "~A~%" (get-output-stream-string out)))))

(defun print-nearest ()
  "кто к какой партии тянется"
  (format t "~%━━━ КУДА ТЯНЕТСЯ ЭЛЕКТОРАТ ━━━~%")
  (dolist (c (citizen-list))
    (multiple-value-bind (pid d) (nearest-party c)
      (let ((pt (party-by-id pid)))
        (format t "  ~A (~A, ~A) → «~A» [~A]~%"
                (g c "name") (g c "age") (g c "job")
                (if pt (g pt "name") "—") (fmt d))))))

(defun print-closest (who)
  (let* ((c (and who (find who (citizen-list) :key (lambda (x) (g x "id")) :test #'equal))))
    (unless c
      (setf c (find who (citizen-list) :key (lambda (x) (g x "name")) :test #'equal)))
    (if (null c)
        (format t "❌ нет гражданина «~A» (нужен id вида p-001 или имя)~%" who)
        (progn
          (format t "~%━━━ КУДА ГОЛОСУЕТ ~A (~A, ~A) ━━━~%"
                  (g c "name") (g c "age") (g c "job"))
          (format t "позиции: ")
          (dolist (ax (axis-ids))
            (format t "~A~A " ax (fmt (axis-val (pos-of c) ax) 1)))
          (format t "~%лояльность: ~A~%" (fmt (num (g c "loyalty") 0.5)))
          (dolist (pt (sort (copy-list (party-list)) #'<
                            :key (lambda (pt) (pos-distance (pos-of c) (pos-of pt)))))
            (format t "  «~A»: расстояние ~A, вес голоса ~A, сходится по: ~A~%"
                    (g pt "name")
                    (fmt (pos-distance (pos-of c) (pos-of pt)))
                    (fmt (support-weight c pt))
                    (or (suggest-axis c pt) "ни по чему (идеальный нейтрал)")))))))

(defun suggest-axis (c pt)
  "по каким осям гражданин и партия сходятся ближе всего"
  (let ((best nil) (best-d 99.0) (worst nil) (worst-d -1.0))
    (dolist (ax (axis-ids))
      (let ((d (abs (- (axis-val (pos-of c) ax) (axis-val (pos-of pt) ax)))))
        (when (< d best-d) (setf best-d d best ax))
        (when (> d worst-d) (setf worst-d d worst ax))))
    (if (and best (< best-d 0.35))
        (format nil "~A (расхождение ~A), спорит по ~A (~A)"
                best (fmt best-d) worst (fmt worst-d))
        (format nil "ни по чему остро, главный спор — ~A (~A)" worst (fmt worst-d)))))

(defun print-leader (party-id)
  (let ((pt (party-by-id party-id)))
    (if (null pt)
        (format t "❌ нет партии «~A»~%" party-id)
        (multiple-value-bind (leader w) (party-leader pt)
          (format t "~%👑 лидер партии «~A» — ~A (~A, ~A), вес ~A~%"
                  (g pt "name") (g leader "name") (g leader "age") (g leader "job") (fmt w))))))

(defun print-distances ()
  (format t "~%━━━ МАТРИЦА РАССТОЯНИЙ ━━━~%")
  (format t "~30A" "гражданин")
  (dolist (pt (party-list)) (format t "~14A" (g pt "id")))
  (terpri)
  (dolist (c (citizen-list))
    (format t "~30A" (format nil "~A ~A" (g c "name") (g c "id")))
    (dolist (pt (party-list))
      (format t "~14A" (fmt (pos-distance (pos-of c) (pos-of pt)))))
    (terpri)))

;; ────────────────────────────── main

(defun main ()
  (let* ((args (rest sb-ext:*posix-argv*))
         (json-out (member "--json" args :test #'equal))
         (*json-out* json-out)
         (cmd (first args)))
    (handler-case
        (cond
          ((null cmd) (load-politics) (print-axes) (print-rate))
          ((string-equal cmd "show") (load-politics) (print-axes) (print-rate))
          ((string-equal cmd "axes") (load-politics) (print-axes))
          ((string-equal cmd "rate")
           (load-politics)
           (if *json-out*
               (print-json-rate)
               (print-rate)))
          ((string-equal cmd "closest") (load-politics) (print-closest (second args)))
          ((string-equal cmd "leader") (load-politics) (print-leader (second args)))
          ((string-equal cmd "distances") (load-politics) (print-distances))
          ((string-equal cmd "nearest") (load-politics) (print-nearest))
          ((string-equal cmd "leaders")
           (load-politics)
           (format t "~%━━━ ЛИДЕРЫ ПАРТИЙ (без повторов) ━━━~%")
           (dolist (pair (unique-leaders))
             (let ((c (cdr pair)))
               (format t "  «~A» → ~A (~A, ~A лет, ~A)~%"
                       (g (party-by-id (car pair)) "name")
                       (g c "name") (g c "id") (g c "age") (g c "job")))))
          (t (format t "неизвестная команда: ~A~%" cmd)))
      (sb-int:simple-file-error (e)
        (format *error-output* "ошибка файла: ~A~%" e))
      (error (e)
        (format *error-output* "ошибка: ~A~%" e)))))

(main)
