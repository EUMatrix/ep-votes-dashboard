import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://ptkemzrjsahaqjjauask.supabase.co'
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB0a2VtenJqc2FoYXFqamF1YXNrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTEzNjM1MDUsImV4cCI6MjA2NjkzOTUwNX0.CtZZ1ORRIstAXeAu0syP1Vyp9qk6iGI2GINnMTiJB5E'

export const supabase = createClient(supabaseUrl, supabaseKey, {
  db: { schema: 'ep_plenary_votes' },
})
