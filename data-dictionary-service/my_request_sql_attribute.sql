DO $$
DECLARE
    v_request_id      text := 'REPLACE_REQUEST_ID';
    v_approver_id     text := 'REPLACE_APPROVER_ID';
    v_approver_name   text := 'REPLACE_APPROVER_NAME';
    v_action          text := 'APPROVE'; -- APPROVE or REJECT
    v_checker_comment text := 'manual test approve/reject';
    v_now             timestamptz := now();

    v_request_exists   int;
    v_attribute_items  int;
    v_dataset_items    int;
BEGIN
    SELECT count(*)
    INTO v_request_exists
    FROM public.approval_request ar
    WHERE ar.request_id = v_request_id
      AND ar.request_status = 'PENDING';

    IF v_request_exists = 0 THEN
        RAISE EXCEPTION 'Request % is not in PENDING status or does not exist', v_request_id;
    END IF;

    SELECT count(*)
    INTO v_attribute_items
    FROM public.attribute_entity_pending ap
    WHERE ap.request_id = v_request_id
      AND ap.approval_status = 'P';

    IF v_attribute_items = 0 THEN
        RAISE EXCEPTION 'Request % has no pending attribute rows', v_request_id;
    END IF;

    SELECT count(*)
    INTO v_dataset_items
    FROM public.table_entity_pending tp
    WHERE tp.request_id = v_request_id
      AND tp.approval_status = 'P';

    IF v_dataset_items > 0 THEN
        RAISE EXCEPTION 'Request % contains dataset pending rows. Use mixed/dataset SQL instead.', v_request_id;
    END IF;

    IF upper(v_action) = 'APPROVE' THEN

        /*
         * 1. 写 attribute history
         * 优先用 pending.current_snapshot；如果为空，则退回主表当前数据
         */
        INSERT INTO public.attribute_entity_history (
            history_id,
            attribute_id,
            metadata,
            version_seq,
            requester_id,
            approver_id,
            requester_ts,
            approver_ts,
            dictionary_action,
            approval_status,
            record_status,
            effective_from,
            effective_to,
            source_request_id,
            archived_at
        )
        SELECT
            gen_random_uuid()::text,
            ap.target_attribute_id,
            COALESCE(ap.current_snapshot, a.metadata),
            COALESCE(ap.current_version_seq, a.version_seq, 1),
            ap.requester_id,
            v_approver_id,
            ap.requester_ts,
            v_now,
            ap.dictionary_action,
            'A',
            COALESCE(a.record_status, 'A'),
            COALESCE(a.effective_from, ap.requester_ts, v_now),
            v_now,
            ap.request_id,
            v_now
        FROM public.attribute_entity_pending ap
        LEFT JOIN public.attribute_entity a
          ON a.id = ap.target_attribute_id
        WHERE ap.request_id = v_request_id
          AND ap.approval_status = 'P'
          AND ap.dictionary_action IN ('U', 'D');

        /*
         * 2. 更新 attribute pending
         */
        UPDATE public.attribute_entity_pending ap
        SET
            approval_status = 'A',
            approver_id = v_approver_id,
            approver_ts = v_now,
            checker_comment = v_checker_comment,
            updated_at = v_now
        WHERE ap.request_id = v_request_id
          AND ap.approval_status = 'P';

        /*
         * 3. 更新 request header
         */
        UPDATE public.approval_request ar
        SET
            request_status = 'APPROVED',
            reviewed_by = v_approver_id,
            reviewed_by_name = v_approver_name,
            reviewed_at = v_now,
            checker_comment = v_checker_comment,
            approved_items = ar.total_items,
            rejected_items = 0,
            updated_at = v_now
        WHERE ar.request_id = v_request_id;

    ELSIF upper(v_action) = 'REJECT' THEN

        /*
         * REJECT 不写 history
         */
        UPDATE public.attribute_entity_pending ap
        SET
            approval_status = 'R',
            approver_id = v_approver_id,
            approver_ts = v_now,
            checker_comment = v_checker_comment,
            updated_at = v_now
        WHERE ap.request_id = v_request_id
          AND ap.approval_status = 'P';

        UPDATE public.approval_request ar
        SET
            request_status = 'REJECTED',
            reviewed_by = v_approver_id,
            reviewed_by_name = v_approver_name,
            reviewed_at = v_now,
            checker_comment = v_checker_comment,
            approved_items = 0,
            rejected_items = ar.total_items,
            updated_at = v_now
        WHERE ar.request_id = v_request_id;

    ELSE
        RAISE EXCEPTION 'Unsupported action: %. Use APPROVE or REJECT.', v_action;
    END IF;
END $$;
