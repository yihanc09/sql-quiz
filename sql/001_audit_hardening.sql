-- Apply with an administrator connection. Existing logs and answers are retained.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

ALTER TABLE public.quiz_audit_log ADD COLUMN IF NOT EXISTS sql_answer text;
ALTER TABLE public.quiz_audit_log ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'legacy';
ALTER TABLE public.quiz_audit_log ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.quiz_audit_log FROM PUBLIC, anon, authenticated, quiz_reader;
-- The identity sequence must not provide an alternate way to manipulate IDs.
DO $block$
DECLARE seq text;
BEGIN
    seq := pg_catalog.pg_get_serial_sequence('public.quiz_audit_log', 'id');
    IF seq IS NOT NULL THEN
        -- %s formats a server-derived regclass identifier, never student input.
        EXECUTE pg_catalog.format('REVOKE ALL ON SEQUENCE %s FROM PUBLIC, anon, authenticated, quiz_reader', seq::regclass);
    END IF;
END;
$block$;

CREATE OR REPLACE FUNCTION public.log_quiz_answer_change()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
BEGIN
    INSERT INTO public.quiz_audit_log
        (user_id, action, question_id, success, sql_answer, source)
    VALUES
        (NEW.user_id,
         CASE WHEN TG_OP = 'INSERT' THEN 'SAVE_ANSWER' ELSE 'UPDATE_ANSWER' END,
         NEW.question_id, true, NEW.sql_answer, 'answer_trigger');
    RETURN NEW;
END;
$function$;

-- Preserve the deployed app's legacy RPC, but distinguish client-reported events
-- from server-observed executions. It cannot supply a user ID, SQL, or source.
CREATE OR REPLACE FUNCTION public.record_quiz_query_event(
    p_question_id integer, p_action text, p_success boolean
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'Authentication required' USING ERRCODE = '42501';
    END IF;
    IF p_action IS NULL OR p_action NOT IN ('RUN_QUERY', 'SUBMIT_QUERY')
       OR p_question_id IS NULL OR p_question_id NOT BETWEEN 1 AND 5
       OR p_success IS NULL THEN
        RAISE EXCEPTION 'Invalid query event' USING ERRCODE = '22023';
    END IF;
    INSERT INTO public.quiz_audit_log (user_id, action, question_id, success, source)
    VALUES (auth.uid(), p_action, p_question_id, p_success, 'client_rpc');
END;
$function$;

REVOKE ALL ON FUNCTION public.log_quiz_answer_change() FROM PUBLIC, anon, authenticated, quiz_reader;
REVOKE ALL ON FUNCTION public.record_quiz_query_event(integer, text, boolean) FROM PUBLIC, anon, quiz_reader;
GRANT EXECUTE ON FUNCTION public.record_quiz_query_event(integer, text, boolean) TO authenticated;

-- Audit writes must be part of the same transaction as the saved answer.
DROP TRIGGER IF EXISTS trg_quiz_answer_audit ON public.quiz_answers;
CREATE TRIGGER trg_quiz_answer_audit
AFTER INSERT OR UPDATE ON public.quiz_answers
FOR EACH ROW EXECUTE FUNCTION public.log_quiz_answer_change();

CREATE OR REPLACE FUNCTION public.reject_quiz_audit_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $function$
BEGIN
    RAISE EXCEPTION 'Quiz audit log is append-only' USING ERRCODE = '42501';
END;
$function$;
REVOKE ALL ON FUNCTION public.reject_quiz_audit_mutation() FROM PUBLIC, anon, authenticated, quiz_reader;

DROP TRIGGER IF EXISTS trg_quiz_audit_no_edit ON public.quiz_audit_log;
CREATE TRIGGER trg_quiz_audit_no_edit BEFORE UPDATE OR DELETE ON public.quiz_audit_log
FOR EACH ROW EXECUTE FUNCTION public.reject_quiz_audit_mutation();
DROP TRIGGER IF EXISTS trg_quiz_audit_no_truncate ON public.quiz_audit_log;
CREATE TRIGGER trg_quiz_audit_no_truncate BEFORE TRUNCATE ON public.quiz_audit_log
FOR EACH STATEMENT EXECUTE FUNCTION public.reject_quiz_audit_mutation();

COMMIT;
