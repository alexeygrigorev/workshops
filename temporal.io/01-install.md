
cli: https://docs.temporal.io/cli

ULR: https://temporal.download/cli/archive/latest?platform=windows&arch=amd64

platform could be: darwin, linux, windows; arch is amd64 or arm64


Download it and put somewhere on the PATH. For me it's `~/bin`:

```bash
wget 'https://temporal.download/cli/archive/latest?platform=windows&arch=amd64' -O temporal.zip
unzip temporal.zip
rm LICENSE temporal.zip
```



Check that it's installed: 

```bash
temporal -v
```


I get this:

```
temporal version 1.5.1 (Server 1.29.1, UI 2.42.1)
```

Start: 

temporal server start-dev

Open your browser: http://localhost:8233

`start-dev` uses an in-memory database. If you persistance, use `--db-filename`:

```bash
temporal server start-dev --db-filename your_temporal.db
```


Note to myself: starting in docker (maybe later will need it for docker-compose)

```bash
docker run --rm -p 7233:7233 -p 8233:8233 temporalio/temporal server start-dev --ip 0.0.0.0
```
