To develop locally, follow the steps below (taken from https://supabase.com/docs/guides/cli/local-development)

### Start local development

`supabase start`

When you see...

``` 
         API URL: http://localhost:54321
     GraphQL URL: http://localhost:54321/graphql/v1
          DB URL: postgresql://postgres:postgres@localhost:54322/postgres
      Studio URL: http://localhost:54323
    Inbucket URL: http://localhost:54324
      JWT secret: super-secret-jwt-token-with-at-least-32-characters-long
        anon key: ***************************
service_role key: ***************************
```

You will use these values into your `.env` in your other folders, like `database` and `website`  

You can access your dashboard using http://localhost:54323/

### Stop local development

`supabase stop`

### If something goes wrong

`supabase db reset` to reset the database

### If you need to remove all docker volumes

`docker rm -vf $(docker ps -aq)`

### Set up for initialization & syncing

`supabase login`

`supabase link --project-ref [Your project ID]`

`supabase db pull`

### To push db changes

`supabase db push`
