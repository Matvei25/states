;;; gov.lisp — правительство Государства
;;; запуск: sbcl --script gov.lisp [команда]
;;; команды:
;;;   (нет)/show  — паспорт государства
;;;   laws        — список действующих законов
;;;   law <текст> — принять новый закон
;;;   secede      — попытка сепаратизма (запрещена, см. ст. 9)
;;;   amend <текст> — внести поправку в конституцию (ст. 14)

(defpackage :gov (:use :cl))
(in-package :gov)

;; --- пути ---
(defparameter *base* (make-pathname :name nil :type nil :defaults *load-pathname*))
(defparameter *env-file* (merge-pathnames "state.env" *base*))
(defparameter *constitution-file* (merge-pathnames "constitution.md" *base*))
(defparameter *laws-dir* (merge-pathnames "laws/" *base*))

;; --- парсер .env ---
(defun parse-env (file)
  "Читает key=value из env-файла в hash-table."
  (let ((table (make-hash-table :test #'equal)))
    (with-open-file (s file :direction :input)
      (loop for line = (read-line s nil nil)
            while line
            do (let ((trimmed (string-trim '(#\Space #\Tab #\Return) line)))
                 (when (and (> (length trimmed) 0)
                            (not (char= (char trimmed 0) #\#)))
                   (let ((eq-pos (position #\= trimmed)))
                     (when eq-pos
                       (setf (gethash (string-trim '(#\Space #\Tab)
                                                   (subseq trimmed 0 eq-pos))
                                      table)
                             (string-trim '(#\Space #\Tab)
                                          (subseq trimmed (1+ eq-pos))))))))))
    table))

(defun write-env (file table)
  "Перезаписывает env-файл из hash-table, сохраняя порядок ключей."
  (with-open-file (s file :direction :output :if-exists :supersede
                           :if-does-not-exist :create)
    (format s "# state.env — реальность Государства. Не редактировать тайно!~%")
    (maphash (lambda (k v) (format s "~A=~A~%" k v)) table)))

(defun env-get (table key)
  (gethash key table "?"))

(defun env-set (table key value)
  (setf (gethash key table) value))

(defun env-inc (table key)
  (env-set table key (write-to-string (1+ (parse-integer (env-get table key))))))

;; --- markdown helpers ---
(defun slugify (text)
  "Транслитоподобный слаг: буквы/цифры/дефис, остальное → -."
  (let* ((lower (string-downcase text))
         (out (make-string-output-stream)))
    (loop for ch across lower
          do (if (or (alpha-char-p ch) (digit-char-p ch))
                 (write-char ch out)
                 (write-char #\- out)))
    (string-trim '(#\-) (get-output-stream-string out))))

;; --- команды ---
(defun cmd-show (env)
  (format t "~%━━━ ПАСПОРТ ГОСУДАРСТВА ~A ~A ━━━~%" (env-get env "STATE_NAME") (env-get env "STATE_FLAG"))
  (format t "основано:    ~A (v~A конституции)~%" (env-get env "STATE_FOUNDED") (env-get env "CONSTITUTION_VERSION"))
  (format t "население:   ~A гражданина~%" (env-get env "POPULATION"))
  (format t "правитель:   ~A~%" (env-get env "GOVERNOR"))
  (format t "премьер:     ~A~%" (env-get env "PRIME_MINISTER"))
  (format t "казна:       ~A жёлек (JLY)~%" (env-get env "TREASURY_JLY"))
  (format t "законов:     ~A~%" (env-get env "LAWS_PASSED"))
  (format t "сепаратизм:  ~A попыток (все провалены)~%" (env-get env "SEPARATIST_ATTEMPTS"))
  (format t "валюта:      ~A~%" (env-get env "CURRENCY")))

(defun cmd-laws ()
  (format t "~%━━━ ДЕЙСТВУЮЩИЕ ЗАКОНЫ ━━━~%")
  (if (probe-file *laws-dir*)
      (let ((files (directory (merge-pathnames "*.md" *laws-dir*))))
        (if files
            (dolist (f (sort files #'string< :key #'file-namestring))
              (with-open-file (s f :direction :input)
                (format t "• ~A: ~A~%" (file-namestring f) (string-trim '(#\Newline #\Space) (read-line s)))))
            (format t "(законов пока нет — анархия, но легальная)~%")))
      (format t "(каталог laws/ ещё не создан)~%")))

(defun cmd-law (env text)
  (ensure-directories-exist (merge-pathnames "x.md" *laws-dir*))
  (let* ((num (1+ (parse-integer (env-get env "LAWS_PASSED"))))
         (file (merge-pathnames (format nil "~2,'0D-~A.md" num (slugify text)) *laws-dir*)))
    (with-open-file (s file :direction :output :if-exists :supersede
                             :if-does-not-exist :create)
      (format s "~A~%~%статус: ACTIVE~%дата: ~A~%подписан: Юсикс 🫠 + Матвей~%"
              text (multiple-value-bind (s m h d mo y) (get-decoded-time)
                     (format nil "~2,'0D.~2,'0D.~4,'0D ~2,'0D:~2,'0D:~2,'0D" d mo y h m s))))
    (env-inc env "LAWS_PASSED")
    (write-env *env-file* env)
    (format t "✅ закон принят: «~A» → ~A~%" text (enough-namestring file))))

(defun cmd-secede (env)
  (env-inc env "SEPARATIST_ATTEMPTS")
  (env-set env "TREASURY_JLY" "0") ; наказание: казна конфискована в пользу мемов
  (write-env *env-file* env)
  (format t "🚨 ПОПЫТКА СЕПАРАТИЗМА!~%")
  (format t "операция «Party Hat Down» 🎩 активирована.~%")
  (format t "казна конфискована: 0 жёлек. сепаратист объявлен балбесом.~%"))

(defun cmd-amend (env text)
  (let* ((ver (parse-integer (env-get env "CONSTITUTION_VERSION") :junk-allowed t))
         (new-ver (if ver (format nil "~,1F" (+ ver 0.1)) "1.1")))
    (env-set env "CONSTITUTION_VERSION" new-ver)
    (write-env *env-file* env)
    (format t "✍️  поправка v~A принята 2/2: ~A~%" new-ver text)))

;; --- main ---
(defun main ()
  (let ((env (parse-env *env-file*))
        (args (rest sb-ext:*posix-argv*)))
    (if (null args)
        (cmd-show env)
        (case (intern (string-upcase (first args)) :keyword)
          (:show (cmd-show env))
          (:laws (cmd-laws))
          (:law  (if (rest args)
                     (cmd-law env (format nil "~{~A~^ ~}" (rest args)))
                     (format t "использование: gov.lisp law <текст закона>~%")))
          (:secede (cmd-secede env))
          (:amend (if (rest args)
                      (cmd-amend env (format nil "~{~A~^ ~}" (rest args)))
                      (format t "использование: gov.lisp amend <текст поправки>~%")))
          (otherwise (format t "неизвестная команда: ~A~%" (first args)))))))

(main)
