from job_search.api.head_hunter_api import HeadHunterAPI


def main():

    a = HeadHunterAPI()
    b = a.get_vacancies("python", per_page=2)

    for i in b:
        print(i)
        print()


if __name__ == "__main__":
    main()
