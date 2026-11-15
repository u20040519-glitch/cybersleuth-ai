-- =============================================================================
-- 009 - Storage buckets
-- =============================================================================
-- Three private buckets. On Supabase these are managed by the Storage API;
-- the statements below are guarded so the file also runs on a plain
-- PostgreSQL instance (where the local filesystem backend is used instead).
-- =============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'storage') THEN
        -- Originals: immutable. There is deliberately NO update policy.
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES ('evidence-originals', 'evidence-originals', false, 104857600, NULL)
        ON CONFLICT (id) DO NOTHING;

        -- Derived artefacts produced by the forensic pipeline.
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES ('evidence-derived', 'evidence-derived', false, 104857600, NULL)
        ON CONFLICT (id) DO NOTHING;

        -- Rendered PDF reports.
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES ('reports', 'reports', false, 52428800, NULL)
        ON CONFLICT (id) DO NOTHING;

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
    END IF;
END
$$;
