import datetime


# всё работает ок, тренажер принял решение
# но в теле функции не используется переданный request
# это ок? ведь даты в нем вроде все равно нет.
def year(request):
    """Добавляет переменную с текущим годом."""
    date = datetime.date.today()
    year = int(date.strftime('%Y'))
    return {
        'year': year
    }
