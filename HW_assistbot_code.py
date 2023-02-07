import telebot
import pandas as pd
import openpyxl
import numpy as np
from telebot import types
import zipfile
import os
from datetime import datetime

def get_user_data(user_id, register_table, real_table):
    """Возвращает личные данные пользователя"""
    registered_users = pd.read_excel(register_table)
    real_user_data = pd.read_excel(real_table)
    user_data = registered_users[registered_users['id'] == user_id]
    surname = list(user_data['Фамилия'])[0]
    name = list(user_data['Имя'])[0]
    patronymic = list(user_data['Отчество'])[0]
    if real_table == 'MyStudents.xlsx':
        condition = (real_user_data['Фамилия'] == surname) & \
                    (real_user_data['Имя'] == name) & \
                    (real_user_data['Отчество'] == patronymic)
        group = list(real_user_data[condition]['Группа'])[0]
        return surname, name, patronymic, group
    else:
        condition = (real_user_data['Фамилия'] == surname) & \
                    (real_user_data['Имя'] == name) & \
                    (real_user_data['Отчество'] == patronymic)
        group = list(real_user_data[condition]['Группа'])
        code = list(real_user_data[condition]['Код предмета'])
        return surname, name, patronymic, group, code


def check_if_registered(user_id, mode='universal'):
    """Возвращает True или False в зависимости от наличия id пользователя
    в таблице с зарегистрированными студентами/преподавателями"""
    registered_students = pd.read_excel('RegisteredStudents.xlsx')
    registered_teachers = pd.read_excel('RegisteredTeachers.xlsx')
    if mode == 'universal':
        if user_id in list(registered_students['id']) + list(registered_teachers['id']):
            return True
        else:
            return False
    elif mode == 'student':
        if user_id in list(registered_students['id']):
            return True
        else:
            return False
    else:
        if user_id in list(registered_teachers['id']):
            return True
        else:
            return False


def save_zip(arch, folder_list, mode, subjects):
    """Сохраняет архив с решениями"""
    z = zipfile.ZipFile(arch, mode, zipfile.ZIP_DEFLATED, True)
    for add_folder in folder_list:
        for root, dirs, files in os.walk(add_folder):
            for file in files:
                if file.split('_')[0] in subjects:
                    path = os.path.join(root, file)
                    z.write(path, os.path.relpath(os.path.join(root, file), os.path.join(root_dir, '..')))
    z.close()


@bot.message_handler(commands=["start"])
def start(message):
    """Приветствие при начале работы с ботом. Вывод необходимой информации для начала работы."""

    def say_hello():
        """Возвращает сообщение с приветствием"""
        if patronymic != '-':
            output_mess = "Приветствуем Вас, " + surname + ' ' + name + ' ' + patronymic + '!\n'
        else:
            output_mess = "Приветствуем Вас, " + surname + ' ' + name + '!\n'
        return output_mess

    def define_available_task(idx):
        """Возвращает True или False в зависимости от доступности задания для сдачи"""

        start_date = list(group_tasks['Дата выдачи'])[idx].date()
        task_to_check = list(group_tasks['Задание'])[idx]
        code = list(group_tasks['Код предмета'])[idx]
        max_score = list(group_tasks['Максимальный балл'])[idx]
        score_data = pd.read_excel('Scores.xlsx', sheet_name=code, header=[0, 1])
        if start_date > mess_date:
            return False
        else:
            try:
                row_idx = score_data.index[score_data[('id', ' ')] == user_id].tolist()[0]
                col_idx = score_data.columns.get_loc((task_to_check, 'баллы'))
                if score_data.iloc[row_idx, col_idx] == max_score:
                    return False
                else:
                    return True
            except IndexError:
                return True

    user_id = message.from_user.id
    if check_if_registered(user_id, 'student'):
        surname, name, patronymic, group = get_user_data(user_id, 'RegisteredStudents.xlsx', 'MyStudents.xlsx')
        mess = say_hello()
        mess += '\nДоступные для сдачи задания:'
        mess_date = datetime.utcfromtimestamp(message.date).date()
        tasks = pd.read_excel('Tasks.xlsx')
        group_tasks = tasks[tasks['Группа'] == group]
        flag = 0
        for i in range(group_tasks.shape[0]):
            if define_available_task(i):
                flag = 1
                if list(group_tasks['Код предмета'])[i] not in mess:
                    mess += '\n' + list(group_tasks['Код предмета'])[i] + '\n'
                mess += '- ' + list(group_tasks['Задание'])[i] + ': дедлайн ' \
                        + list(group_tasks['Крайний срок'])[i].strftime('%d-%m-%Y') + '\n'
        if flag == 0:
            mess += '\nНа данный момент нет доступных заданий.'
        else:
            mess += '\nБолее подробную информацию о задаче можно узнать /info имя_задачи'
        bot.send_message(message.from_user.id, mess)
    elif check_if_registered(user_id, 'teacher'):
        surname, name, patronymic, _ = get_user_data(user_id, 'RegisteredTeachers.lsx', 'Teachers.xlsx')
        mess = say_hello()
        bot.send_message(message.from_user.id, mess)
    else:
        for i in range(5):
            bot.send_message(message.from_user.id, bot_answers['Hello'][i])


@bot.message_handler(commands=["help"])
def get_help(message):
    """Справка по боту"""
    user_id = message.from_user.id
    if not check_if_registered(user_id, 'universal'):
        bot.send_message(message.from_user.id, bot_answers['NotRegistered'])
    elif check_if_registered(user_id, 'student'):
        bot.send_message(message.from_user.id, bot_answers['StudentsCommands'])
    elif check_if_registered(user_id, 'teacher'):
        bot.send_message(message.from_user.id, bot_answers['TeachersCommands'])


@bot.message_handler(commands=["register"])
def register(message):
    """Регистрация пользователя. Добавление ФИО и id в таблицу с зарегистрированными пользователями"""
    @bot.callback_query_handler(func=lambda call: True)
    def callback_worker(call):
        """Подтверждение роли пользователя"""
        if call.data == "student":
            save_information('MyStudents.xlsx', 'RegisteredStudents.xlsx')
        else:
            bot.send_message(message.from_user.id, bot_answers['PassRequest'])
            bot.register_next_step_handler(message, check_password)

    def check_password(input_message):
        input_pass = input_message.text
        if input_pass == 'Торжественно клянусь, что я преподаватель!':
            save_information('Teachers.xlsx', 'RegisteredTeachers.xlsx')
        else:
            bot.send_message(message.from_user.id, bot_answers['WrongPass'])
            bot.register_next_step_handler(message, register)

    def save_information(check_table, table_to_save):
        new_row = [user_id, user_name, surname, name, patronymic]
        real_people = pd.read_excel(check_table)
        this_person_row = real_people[
            (real_people['Фамилия'] == surname) &
            (real_people['Имя'] == name) &
            (real_people['Отчество'] == patronymic)
        ]
        registered_person = pd.read_excel(table_to_save)
        if this_person_row.shape[0] > 0:
            if user_id not in list(registered_person['id']):
                registered_person.loc[len(registered_person.index)] = new_row
                registered_person.to_excel(table_to_save, index=False)
                bot.send_message(message.from_user.id, "Пользователь " + full_name + " успешно зарегистрирован!")
            else:
                bot.send_message(message.from_user.id, bot_answers['AlreadyExists'])
        else:
            bot.send_message(message.from_user.id, bot_answers['NoUser'])

    full_name = message.text
    user_id = message.from_user.id
    user_name = message.from_user.username
    name_list = full_name.split()

    if (len(name_list) < 5) and (len(name_list) > 2):
        if len(name_list) == 4:
            patronymic = name_list[3]
            name = name_list[2]
            surname = name_list[1]
            full_name = surname + ' ' + name + ' ' + patronymic
        else:
            patronymic = '-'
            name = name_list[2]
            surname = name_list[1]
            full_name = surname + ' ' + name

        keyboard_role = types.InlineKeyboardMarkup()
        key_stud = types.InlineKeyboardButton(text='Студент', callback_data='student')
        key_teach = types.InlineKeyboardButton(text='Преподаватель', callback_data='teacher')
        keyboard_role.add(key_stud)
        keyboard_role.add(key_teach)
        question_role = bot_answers['Role']
        bot.send_message(message.from_user.id, text=question_role, reply_markup=keyboard_role)
    else:
        bot.send_message(message.from_user.id, bot_answers['WrongRegister'])
        bot.register_next_step_handler(message, register)


@bot.message_handler(commands=["info"])
def get_info(message):
    """Выводит информацию о задании"""
    user_id = message.from_user.id
    _, _, _, group = get_user_data(user_id, 'RegisteredStudents.xlsx', 'MyStudents.xlsx')
    src = root_dir + 'Information/' + group + '/'
    mess_text = message.text
    task = mess_text.split()[-1]
    all_tasks = pd.read_excel('Tasks.xlsx')
    length = len(list(all_tasks['Задание']))
    if task in np.array(all_tasks['Код предмета']) + np.array(['_'] * length) + np.array(all_tasks['Задание']):
        src += task + '.txt'
        with open(src) as f:
            lines = f.readlines()
        task_info = ''
        for line in lines:
            task_info += line
        bot.send_message(message.from_user.id, task_info)
    else:
        bot.send_message(message.from_user.id, bot_answers['WrongTaskName'])


@bot.message_handler(content_types=['document', 'caption'])
def handle_docs(message):
    """Получает файл задания и сохраняет его"""
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        task_name = message.caption
        fn = message.document.file_name
        user_id = message.from_user.id
        tasks = pd.read_excel('Tasks.xlsx')
        surname, name, patronymic, group = get_user_data(user_id, 'RegisteredStudents.xlsx', 'MyStudents.xlsx')

        saving_folder = root_dir + 'Receives/' + group + '/' + str(user_id) + '/'
        if not os.path.exists(saving_folder):
            os.makedirs(saving_folder)
        length = len(list(tasks['Задание']))
        task_file = fn.split('.')
        if task_file[0] == task_name:
            if task_name in np.array(tasks['Код предмета']) + np.array(['_'] * length) + \
                    np.array(tasks['Задание']):
                if patronymic != '-':
                    bot.reply_to(message, "Задание " + task_name + 'от учащегося ' + surname + ' ' + name +
                                 ' ' + patronymic + ' успешно принято.')
                else:
                    bot.reply_to(message, "Задание " + task_name + 'от учащегося ' + surname + ' ' + name +
                                 ' успешно принято.')
                with open(saving_folder + fn, 'wb') as new_file:
                    new_file.write(downloaded_file)
            else:
                bot.send_message(message.from_user.id, bot_answers['WrongTaskRepeat'])
        else:
            bot.send_message(message.from_user.id, bot_answers['WrongCaption'])
    except Exception as e:
        bot.reply_to(message, e)


# проблемы сс форматом сохранения
@bot.message_handler(commands=["check"])
def check(message):
    """Осущетвляет проверку заданий"""

    def standard_mess(student_score, maximum_score, student_tries, student_weight):
        """Возвращает стандратное сообщение с набранными баллами и количеством попыток"""
        st_mess = f'Задание решено на {student_score} баллов из {maximum_score}. ' \
                  f'Всего количество попыток: {student_tries}. ' \
                  f'Итоговый балл {round(student_weight * student_score, 1)}. '
        return st_mess

    def write_excel(filename, sheetname, dataframe):
        with pd.ExcelWriter(filename, engine='openpyxl', mode='a') as writer:
            work_book = writer.book
            work_book.remove(work_book[sheetname])
            dataframe.to_excel(writer, sheet_name=sheetname)
            writer.save()

    mess = message.text
    all_task_to_check = mess.split()[-1]
    answers_file = all_task_to_check + '.txt'
    solution_file = all_task_to_check + '.pdf'
    user_id = message.from_user.id
    surname, name, patronymic, group = get_user_data(user_id, 'RegisteredStudents.xlsx', 'MyStudents.xlsx')

    tasks_data = pd.read_excel('Tasks.xlsx')
    try:
        code, task_to_check = all_task_to_check.split('_')
    except ValueError:
        bot.send_message(message.from_user.id, bot_answers['TaskNameIncorrect'])
        return None
    condition = (tasks_data['Задание'] == task_to_check) & \
                (tasks_data['Код предмета'] == code) & \
                (tasks_data['Группа'] == group)
    this_task_data = tasks_data[condition]
    if this_task_data.shape[0] > 0:
        txt_src = root_dir + 'Receives/' + group + '/' + str(user_id) + '/' + answers_file
        pdf_src = root_dir + 'Receives/' + group + '/' + str(user_id) + '/' + solution_file

        score_data = pd.read_excel('Scores.xlsx', sheet_name=code, header=[0, 1])
        score_data = score_data.iloc[:, 1::]
        if score_data[(score_data[('id', ' ')] == user_id)].shape[0] == 0:
            row_idx = len(score_data.index)
            score_data.loc[row_idx, ('id', ' ')] = user_id
            score_data.loc[row_idx, ('Фамилия', ' ')] = surname
            score_data.loc[row_idx, ('Имя', ' ')] = name
            score_data.loc[row_idx, ('Отчество', ' ')] = patronymic
            write_excel('Scores.xlsx', code, score_data)

        row_idx = score_data.index[score_data[('id', ' ')] == user_id].tolist()[0]
        col_idx = score_data.columns.get_loc((task_to_check, 'файл txt'))
        if os.path.isfile(txt_src):
            score_data.iloc[row_idx, col_idx] = 1
        else:
            bot.send_message(message.from_user.id, bot_answers['NoTXT'])
            return None
        col_idx = score_data.columns.get_loc((task_to_check, 'файл pdf'))
        if os.path.isfile(pdf_src):
            score_data.iloc[row_idx, col_idx] = 1
        else:
            bot.send_message(message.from_user.id, bot_answers['NoPDF'])
            return None

        mess_date = datetime.utcfromtimestamp(message.date).date()
        deadline = list(this_task_data['Крайний срок'])[0].date()
        col_idx = score_data.columns.get_loc((task_to_check, 'дата сдачи'))
        score_data.iloc[row_idx, col_idx] = mess_date
        col_idx = score_data.columns.get_loc((task_to_check, 'количество попыток'))
        if pd.isnull(score_data.iloc[row_idx, col_idx]):
            score_data.iloc[row_idx, col_idx] = 1
        else:
            score_data.iloc[row_idx, col_idx] = score_data.iloc[row_idx, col_idx] + 1
        tries = score_data.iloc[row_idx, col_idx]

        if list(this_task_data['Автопроверка'])[0]:
            tf = open(txt_src)
            student_answer_list = tf.readlines()
            tf.close()
            tf = open(root_dir + 'Answers/' + group + '/' + answers_file)
            answer_list = tf.readlines()
            tf.close()

            score = 0
            task_amount = len(answer_list)
            max_score = list(this_task_data['Максимальный балл'])[0]
            score_for_one = max_score / task_amount
            if score_data.iloc[row_idx, score_data.columns.get_loc((task_to_check, 'баллы'))] == max_score:
                bot.send_message(message.from_user.id, bot_answers['AlreadyChecked'])
                return None

            for i in range(task_amount):
                try:
                    if float(student_answer_list[i]) == float(answer_list[i]):
                        score += score_for_one
                except (ValueError, IndexError):
                    bot.send_message(message.from_user.id, bot_answers['CheckError'] +
                                     f' Количество попыток: {tries - 1}')
                    return None
            col_idx = score_data.columns.get_loc((task_to_check, 'баллы'))
            score_data.iloc[row_idx, col_idx] = score

            if score < max_score:
                weight = 0
                bot.send_message(
                    message.from_user.id,
                    standard_mess(score, max_score, tries, weight) + bot_answers['NoAbsolute']
                )
            elif mess_date > deadline:
                weight = list(this_task_data['Минимальный балл'])[0] / max_score
                bot.send_message(
                    message.from_user.id,
                    standard_mess(score, max_score, tries, weight) + bot_answers['Deadline']
                )
            elif tries > 3:
                if tries <= 10:
                    diff_score = (max_score - list(this_task_data['Минимальный балл'])[0]) / 7
                    weight = (max_score - diff_score * (tries - 3)) / max_score
                    bot.send_message(
                        message.from_user.id,
                        standard_mess(score, max_score, tries, weight) + bot_answers['Tries3']
                    )
                else:
                    weight = list(this_task_data['Минимальный балл'])[0] / max_score
                    bot.send_message(
                        message.from_user.id,
                        standard_mess(score, max_score, tries, weight) + bot_answers['Tries10']
                    )
            else:
                weight = 1
                bot.send_message(
                    message.from_user.id,
                    standard_mess(score, max_score, tries, weight))
            col_idx = score_data.columns.get_loc((task_to_check, 'вес'))
            score_data.iloc[row_idx, col_idx] = weight
            col_idx = score_data.columns.get_loc((task_to_check, 'итого'))
            total_score = score * weight
            score_data.iloc[row_idx, col_idx] = total_score
        else:
            bot.send_message(message.from_user.id, f'Автопроверка для задания {task_to_check} непредусмотрена. '
                                                   'Дождитесь, пока задание проверит преподаватель.')
        write_excel('Scores.xlsx', code, score_data)

    else:
        bot.send_message(message.from_user.id, f'Задания {task_to_check} нет в списке. '
                                               f'Выполните /start для списка доступных заданий.')


@bot.message_handler(commands=["get"])
def get(message):
    """Отправляет студенту файл с заданием"""
    user_id = message.from_user.id
    surname, name, patronymic, group = get_user_data(user_id, 'RegisteredStudents.xlsx', 'MyStudents.xlsx')
    mess = message.text
    task_to_give = mess.split()[-1]
    task_src = root_dir + 'Tasks/' + group + '/' + task_to_give + '.pdf'
    if os.path.isfile(task_src):
        f = open(task_src, "rb")
        bot.send_document(message.chat.id, f)
    else:
        bot.send_message(message.from_user.id, f'Файл задания {task_to_give} отсутствует. '
                                               'Проверьте правильность названия задания или '
                                               'обратитесь к преподавателю.')


@bot.message_handler(commands=["status"])
def status(message):
    """Выводит полную информацию о баллах студента"""
    user_id = message.from_user.id
    if check_if_registered(user_id, 'student'):
        _, _, _, group = get_user_data(user_id, 'RegisteredStudents.xlsx', 'MyStudents.xlsx')
        tasks = pd.read_excel('Tasks.xlsx')
        group_tasks = tasks[tasks['Группа'] == group]
        mess = ''
        max_sum = 0
        score_sum = 0
        for i in range(group_tasks.shape[0]):
            task = list(group_tasks['Задание'])[i]
            code = list(group_tasks['Код предмета'])[i]
            if code not in mess:
                if i != 0:
                    mess += 'Итого: ' + str(score_sum) + ' из ' + str(max_sum) + '\n'
                mess += '\n' + code + '\n'
                max_sum = group_tasks[group_tasks['Код предмета'] == code]['Максимальный балл'].sum()
                score_sum = 0
            score_data = pd.read_excel('Scores.xlsx', header=[0, 1], sheet_name=code)
            row_idx = score_data.index[score_data[('id', ' ')] == user_id].tolist()[0]
            col_idx = score_data.columns.get_loc((task, 'итого'))
            if np.isnan(score_data.iloc[row_idx, col_idx]):
                mess += task + ': 0' + '\n'
            else:
                task_max = str(list(group_tasks[(group_tasks['Задание'] == task) &
                                                (group_tasks['Код предмета'] == code)]['Максимальный балл'])[0])
                score_sum += score_data.iloc[row_idx, col_idx].round(1)
                mess += task + ': ' + str(score_data.iloc[row_idx, col_idx].round(1)) + ' из ' + task_max + '\n'
        mess += 'Итого: ' + str(score_sum) + ' из ' + str(max_sum) + '\n'
        bot.send_message(message.from_user.id, mess)
    else:
        bot.send_message(message.from_user.id, bot_answers['NotRegistered'])


@bot.message_handler(commands=["solutions"])
def solutions(message):
    mess = message.text
    group_to_send = mess.split()[-1]
    user_id = message.from_user.id
    if check_if_registered(user_id, 'teacher'):
        _, _, _, groups, code = get_user_data(user_id, 'RegisteredTeachers.xlsx', 'Teachers.xlsx')
        if group_to_send == 'all':
            arch_name = 'Решения всех групп'
            backup_folders = []
            codes = code
            for group in groups:
                if root_dir + 'Receives/' + group not in backup_folders:
                    backup_folders.append(root_dir + 'Receives/' + group)
                    backup_folders.append(root_dir + 'Tasks/' + group)
                    backup_folders.append(root_dir + 'Answers/' + group)
        elif group_to_send in groups:
            teachers_info = pd.read_excel('Teachers.xlsx')
            codes = teachers_info[teachers_info['Группа'] == group_to_send]['Код предмета'].tolist()
            arch_name = root_dir + 'Решения группы ' + group_to_send
            backup_folders = [root_dir + 'Receives/' + group_to_send, root_dir + 'Tasks/' + group_to_send,
                              root_dir + 'Answers/' + group_to_send]
        else:
            bot.send_message(message.from_user.id, bot_answers['NoTeacherGroup'])
            return None
        save_zip(arch_name, backup_folders, "w", codes)
        f = open(arch_name, "rb")
        bot.send_document(message.chat.id, f)
    else:
        bot.send_message(message.from_user.id, bot_answers['NotRegistered'])


@bot.message_handler(commands=["report"])
def report(message):

    def send_report(current_group):
        my_students = all_students[all_students['Группа'] == current_group].loc[:, ['Фамилия', 'Имя', 'Отчество']]
        teachers_info = pd.read_excel('Teachers.xlsx')
        condition = (teachers_info['Группа'] == current_group) & (teachers_info['Фамилия'] == surname) & \
                    (teachers_info['Имя'] == name) & (teachers_info['Отчество'] == patronymic)
        this_group_codes = teachers_info[condition]['Код предмета'].tolist()
        for subject in this_group_codes:
            this_subject_info = tasks[(tasks['Группа'] == current_group) & (tasks['Код предмета'] == subject)]
            this_sub_tasks = this_subject_info['Задание'].tolist()
            this_sub_min = this_subject_info['Минимальный балл'].tolist()
            this_sub_max = this_subject_info['Максимальный балл'].tolist()
            num = len(this_sub_tasks)
            highest_lvl = [codes_and_subjects[subject] + ' ' + current_group] * ((num * 3) + 6)
            medium_lvl = ["Студент"] * 3
            content = []
            for i, task in enumerate(this_sub_tasks):
                medium_lvl += [task] * 3
                content += [0, this_sub_min[i], this_sub_max[i]]
            content += [0, sum(this_sub_min), sum(this_sub_max)]
            medium_lvl += ["Итого"] * 3
            lowest_lvl = ["Фамилия", "Имя", "Отчество"] + ['балл', 'min', 'max'] * (num + 1)
            header_list = [highest_lvl, medium_lvl, lowest_lvl]

            main_content_arr = np.tile(np.array(content), (my_students.shape[0], 1))
            main_content_df = pd.DataFrame(main_content_arr)
            whole_content = pd.concat([my_students, main_content_df], axis=1, ignore_index=True)
            df_to_save = pd.DataFrame(whole_content.to_numpy(), columns=header_list)

            score_data = pd.read_excel('Scores.xlsx', sheet_name=subject, header=[0, 1])
            for j in range(len(my_students)):
                row_condition = (score_data[('Фамилия', ' ')] == my_students.iloc[j, 0]) & \
                                (score_data[('Имя', ' ')] == my_students.iloc[j, 1]) & \
                                (score_data[('Отчество', ' ')] == my_students.iloc[j, 2])
                col_condition = list(zip(this_sub_tasks, ['итого'] * num))
                students_scores = score_data[row_condition][col_condition]
                if not students_scores.empty:
                    df_to_save.iloc[j, list(range(3, num * 3 + 3, 3))] = \
                        np.around(students_scores.to_numpy()[0], 1)
                    df_to_save.iloc[j, num * 3 + 3] = np.around(np.sum(students_scores.to_numpy()[0]), 1)
            rep_name = 'Report_' + group_to_send + '_' + subject + '.xlsx'
            df_to_save.to_excel(rep_name)
            f = open(rep_name, "rb")
            bot.send_document(message.chat.id, f)

    mess = message.text
    group_to_send = mess.split()[-1]
    user_id = message.from_user.id
    if check_if_registered(user_id, 'teacher'):
        surname, name, patronymic, groups, code = get_user_data(user_id, 'RegisteredTeachers.xlsx', 'Teachers.xlsx')
        all_students = pd.read_excel('MyStudents.xlsx')
        tasks = pd.read_excel('Tasks.xlsx')
        if group_to_send == 'all':
            for group in groups:
                send_report(group)
        elif group_to_send in groups:
            send_report(group_to_send)
        else:
            bot.send_message(message.from_user.id, bot_answers['NoTeacherGroup'])
            return None
    else:
        bot.send_message(message.from_user.id, bot_answers['NotRegistered'])


if __name__ == '__main__':
    bot_answers = {
        'NoUser': 'Пользователя с такими ФИО нет в списках. Регистрация невозможна. '
                  'Проверьте правильность введённых данных.',
        'WrongRegister': 'Для регистрации необходимы Фамилия и Имя. Повторите ввод.',
        'AlreadyExists': 'Пользователь с таким id уже существует. При необходимости изменить данные '
                         'обратитесь в тех.поддержку..',
        'WrongTaskName': 'Неправильное имя задания, см. список доступных заданий /start',
        'WrongTaskRepeat': 'Некорректное имя задания. Повторите отправку.',
        'WrongCaption': 'Имя задания в caption и названии файла не совпадают. Повторите отправку.',
        'AlreadyChecked': 'Данное задание уже было проверено. Окончательный балл за него выставлен. '
                          'Для проверки баллов воспользуйтесь командой /status',
        'CheckError': 'При проверке отправленного решения возникла ошибка. '
                      'Убедитесь, что количество ответов в отправленном файле соответствует количеству '
                      'заданий (подпункты а, б, в и т.д. считаются отдельными заданиями и должны '
                      'быть записаны в отдельные строки текстового файла). Убедитесь, '
                      'что в отправленном файле отсутствуют какие-либо символы, кроме цифр, знака '
                      'минуса и точки. После исправлений повторите попытку. В случае, если Вы '
                      'уверены в правильности заполненного файла, обратитесь к преподавателю. '
                      'Данная проверка не считается за попытку.',
        'Hello': ['Приветствуем Вас в автоматической системе проверки!',
                  'Вам необходимо вполнить регистрацию аккаунта.',
                  'Выполните /register Фамилия Имя Отчество (при наличии).',
                  'Выполните /help для списка доступных команд.',
                  'Внимание! После регистрации невозможно изменить привязку идентификатора '
                  'Telegram аккаунта к ФИО! Нельзя зарегистрировать несколько пользователей с одного аккаунта!'
                  ],
        'NotRegistered': 'Пользователь незарегистрирован. Выполните /register для начала работы с ботом.\n\n'
                         'Пример:\n/register Иванов Иван Иванович',
        'StudentsCommands': 'Список доступных комманд: \n/start -- список доступных заданий\n'
                            '/register -- регистрация\n/info -- получить информацию о задании\n'
                            '/get -- получить задание\n/check - запуск автоматической проверки задания\n'
                            'загрузка файлов с решениями: для отправки решения необходимо приложить файл'
                            ' и в поле caption ввести имя задания (например, МатАн_ДЗ1)\n'
                            '/status - получить информацию о сданных заданиях и баллах\n\n'
                            'Примеры выполнения команд:\n/start\n/register Иванов Иван Иванович\n'
                            '/info МатАн_ДЗ1\n/get МатАн_ДЗ1\n/check МатАн_ДЗ1',
        'TeachersCommands': 'Список доступных комманд: \n/register -- регистрация\n'
                            '/solutions -- получить архив с решениями\n/report -- получить отчёт\n\n'
                            'Примеры выполнения команд:\n/register Иванов Иван Иванович\n'
                            '/solutions ФН1-21Б или /solutions all\n /report ФН1-21Б или /report all',
        'TaskNameIncorrect': 'Некорректное имя задания. Повторите попытку.',
        'Role': 'Выберите подходящий для Вас вариант регистрации:',
        'WrongPass': 'Пароль неверный. Повторите /register Фамилия Имя Отчество',
        'PassRequest': 'Введите пароль, подтверждающий, что Вы преподаватель:',
        'NoTXT': 'Автопроверка невозможна. Отправьте файл формата txt. '
                 'Подробнее /info имя_задания. Данная отправка не считается за попытку.',
        'NoPDF': 'Отсутствует файл с решением формата .pdf. Отправьте файл с решением, а затем повторите '
                'команду /check',
        'NoAbsolute': 'Задание решено с ошибками, поэтому не считается сданным! '
                      'Исправьте ошибки, отправьте необходимые файлы заново и повторите попытку. '
                      'В случае несовпадения файла решения с ответами преподаватель имеет право '
                      'внести коррективы в проставленные ботом баллы.',
        'Deadline': 'Итоговый балл минимальный, т.к. крайний срок сдачи истёк.',
        'Tries3': 'Итоговый балл меньше максимального, т.к. количество попыток превысило 3.',
        'Tries10': 'Итоговый балл минимальный, т.к. количество попыток превысило 10.',
        'NoTeacherGroup': 'Решённые задания группы может получать только преподаватель, '
                          'который ведёт у этой группы занятия. Проверьте название группы. Если оно верно, '
                          'обратитесь в техподдержку.'
    }
    codes_and_subjects = {
        'МатАн': 'Математический анализ.',
        'ЛинАл': 'Линейная алгебра.',
        'ФНП': 'Функции нескольких переменных'
    }
    root_dir = '/home/anastasia/Документы/Bots/'
    bot.polling(none_stop=True, interval=0)
