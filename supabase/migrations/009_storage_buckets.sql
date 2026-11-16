-- =============================================================================
-- 009 - Storage buckets
-- =============================================================================
-- Three private buckets. On Supabase these are managed by the Storage API;
-- the statements below are guarded so the file also runs on a plain
-- PostgreSQL instance (where the local filesystem backend is used instead).
--
-- The whole block is exception safe: on a platform where the storage schema
-- exists but is owned by somebody else (Supabase: supabase_storage_admin) the
-- individual steps report a NOTICE and the migration still succeeds. A failed
-- bucket bootstrap must never take the whole schema down with it.
-- =============================================================================

DO $buckets$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'storage') THEN
        RAISE NOTICE '009: no storage schema on this server - skipping bucket setup';
        RETURN;
    END IF;

    -- -------------------------------------------------------------------------
    -- Buckets
    -- -------------------------------------------------------------------------
    -- Only the minimal column list is inserted. Supabase's storage.buckets
    -- carries platform owned columns (owner) that are NOT NULL and have no
    -- usable default, so inserting the full column list aborted the entire
    -- DO block on that platform. `public` is the only flag the application
    -- cares about here, and it is false for all three buckets.
    -- -------------------------------------------------------------------------
    BEGIN
        -- Originals: immutable. There is deliberately NO update policy.
        INSERT INTO storage.buckets (id, name, public)
        VALUES ('evidence-originals', 'evidence-originals', false)
        ON CONFLICT (id) DO NOTHING;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE '009: could not create bucket evidence-originals: %', SQLERRM;
    END;

    BEGIN
        -- Derived artefacts produced by the forensic pipeline.
        INSERT INTO storage.buckets (id, name, public)
        VALUES ('evidence-derived', 'evidence-derived', false)
        ON CONFLICT (id) DO NOTHING;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE '009: could not create bucket evidence-derived: %', SQLERRM;
    END;

    BEGIN
        -- Rendered PDF reports.
        INSERT INTO storage.buckets (id, name, public)
        VALUES ('reports', 'reports', false)
        ON CONFLICT (id) DO NOTHING;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE '009: could not create bucket reports: %', SQLERRM;
    END;

    -- -------------------------------------------------------------------------
    -- Bucket limits
    -- -------------------------------------------------------------------------
    -- Applied separately from the insert so that an existing bucket (created
    -- through the Storage API, with a different set of columns) still ends up
    -- with the limits this project expects.
    -- -------------------------------------------------------------------------
    BEGIN
        UPDATE storage.buckets
           SET file_size_limit = 104857600, allowed_mime_types = NULL
         WHERE id = 'evidence-originals';

        UPDATE storage.buckets
           SET file_size_limit = 104857600, allowed_mime_types = NULL
         WHERE id = 'evidence-derived';

        UPDATE storage.buckets
           SET file_size_limit = 52428800, allowed_mime_types = NULL
         WHERE id = 'reports';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE '009: could not apply the bucket limits: %', SQLERRM;
    END;

    -- -------------------------------------------------------------------------
    -- Object policies
    -- -------------------------------------------------------------------------
    BEGIN
        -- Evidence originals may be written by members of the owning
        -- investigation, and never updated or deleted.
        DROP POLICY IF EXISTS "evidence originals insert" ON storage.objects;
        CREATE POLICY "evidence originals insert" ON storage.objects
            FOR INSERT WITH CHECK (
                bucket_id = 'evidence-originals'
                AND EXISTS (
                    SELECT 1 FROM public.investigation_members m
                    WHERE m.investigation_id::text = (storage.foldername(name))[1]
                      AND m.user_id = public.current_user_id()
                )
            );

        DROP POLICY IF EXISTS "evidence originals select" ON storage.objects;
        CREATE POLICY "evidence originals select" ON storage.objects
            FOR SELECT USING (
                bucket_id = 'evidence-originals'
                AND EXISTS (
                    SELECT 1 FROM public.investigation_members m
                    WHERE m.investigation_id::text = (storage.foldername(name))[1]
                      AND m.user_id = public.current_user_id()
                )
            );

        -- Derived artefacts and reports follow the same membership rule.
        DROP POLICY IF EXISTS "evidence derived insert" ON storage.objects;
        CREATE POLICY "evidence derived insert" ON storage.objects
            FOR INSERT WITH CHECK (
                bucket_id = 'evidence-derived'
                AND EXISTS (
                    SELECT 1 FROM public.investigation_members m
                    WHERE m.investigation_id::text = (storage.foldername(name))[1]
                      AND m.user_id = public.current_user_id()
                )
            );

        DROP POLICY IF EXISTS "evidence derived select" ON storage.objects;
        CREATE POLICY "evidence derived select" ON storage.objects
            FOR SELECT USING (
                bucket_id = 'evidence-derived'
                AND EXISTS (
                    SELECT 1 FROM public.investigation_members m
                    WHERE m.investigation_id::text = (storage.foldername(name))[1]
                      AND m.user_id = public.current_user_id()
                )
            );

        DROP POLICY IF EXISTS "reports insert" ON storage.objects;
        CREATE POLICY "reports insert" ON storage.objects
            FOR INSERT WITH CHECK (
                bucket_id = 'reports'
                AND EXISTS (
                    SELECT 1 FROM public.investigation_members m
                    WHERE m.investigation_id::text = (storage.foldername(name))[1]
                      AND m.user_id = public.current_user_id()
                )
            );

        DROP POLICY IF EXISTS "reports select" ON storage.objects;
        CREATE POLICY "reports select" ON storage.objects
            FOR SELECT USING (
                bucket_id = 'reports'
                AND EXISTS (
                    SELECT 1 FROM public.investigation_members m
                    WHERE m.investigation_id::text = (storage.foldername(name))[1]
                      AND m.user_id = public.current_user_id()
                )
            );
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE '009: could not install the storage.objects policies: %', SQLERRM;
    END;
END
$buckets$;
