import compile

FILE_PATH = "query.wmiq"

def main():
    with open(FILE_PATH) as f:
        data = f.read()
    query = compile.compile(data, True)
    print(query)

if __name__ == "__main__":
    main()
