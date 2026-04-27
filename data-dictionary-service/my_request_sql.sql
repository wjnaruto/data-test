BEGIN;

DO $$
DECLARE
    v_request_id      text := 'REPLACE_REQUEST_ID';
    v_approver_id     text := 'REPLACE_APPROVER_ID';
    v_approver_name   text := 'REPLACE_APPROVER_NAME';
    v_action          text := 'APPROVE'; -- APPROVE or REJECT
    v_checker_comment text := 'manual test approve/reject';
    v_now             timestamptz := now();

    v_request_exists  int;
    v_dataset_items   int;
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
    INTO v_dataset_items
    FROM public.table_entity_pending p
    WHERE p.request_id = v_request_id
      AND p.approval_status = 'P'
      AND p.dictionary_action = 'D';

    IF v_dataset_items = 0 THEN
        RAISE EXCEPTION 'Request % has no pending dataset delete rows', v_request_id;
    END IF;

    IF upper(v_action) = 'APPROVE' THEN

        /*
         * 1. 写 dataset history
         * 优先用 pending.current_snapshot；如果为空，则退回主表当前数据
         */
        INSERT INTO public.table_entity_history (
            history_id,
            table_id,
            table_metadata,
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
            p.target_table_id,
            COALESCE(p.current_snapshot, t.table_metadata),
            COALESCE(p.current_version_seq, t.version_seq, 1),
            p.requester_id,
            v_approver_id,
            p.requester_ts,
            v_now,
            'D',
            'A',
            COALESCE(t.record_status, 'A'),
            COALESCE(t.effective_from, p.requester_ts, v_now),
            v_now,
            p.request_id,
            v_now
        FROM public.table_entity_pending p
        LEFT JOIN public.table_entity t
          ON t.id = p.target_table_id
        WHERE p.request_id = v_request_id
          AND p.approval_status = 'P'
          AND p.dictionary_action = 'D';

        /*
         * 2. 写 child attributes history
         * 因为 dataset delete 不会单独生成 child attribute pending，
         * 这里直接从主表 attribute_entity 归档当前 active attributes
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
            a.id,
            a.metadata,
            COALESCE(a.version_seq, 1),
            p.requester_id,
            v_approver_id,
            p.requester_ts,
            v_now,
            'D',
            'A',
            COALESCE(a.record_status, 'A'),
            COALESCE(a.effective_from, p.requester_ts, v_now),
            v_now,
            p.request_id,
            v_now
        FROM public.table_entity_pending p
        JOIN public.attribute_entity a
          ON a.table_id = p.target_table_id
        WHERE p.request_id = v_request_id
          AND p.approval_status = 'P'
          AND p.dictionary_action = 'D'
          AND COALESCE(a.record_status, 'A') = 'A';

        /*
         * 3. 更新 dataset pending
         */
        UPDATE public.table_entity_pending p
        SET
            approval_status = 'A',
            approver_id = v_approver_id,
            approver_ts = v_now,
            checker_comment = v_checker_comment,
            updated_at = v_now
        WHERE p.request_id = v_request_id
          AND p.approval_status = 'P';

        /*
         * 4. 如果 request 下有 attribute pending，也一并标记
         * 对 dataset delete 正常来说通常没有
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
         * 5. 更新 request header
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
         * REJECT 不写 history，只改 request + pending
         */

        UPDATE public.table_entity_pending p
        SET
            approval_status = 'R',
            approver_id = v_approver_id,
            approver_ts = v_now,
            checker_comment = v_checker_comment,
            updated_at = v_now
        WHERE p.request_id = v_request_id
          AND p.approval_status = 'P';

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

COMMIT;
