import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import uuid

TOKEN = '8177017432:AAF913uU6Dk3u65xk2L4msFUbJFF8IKCYaE'
bot = telebot.TeleBot(TOKEN)

user_quizzes = {}  # Store quizzes by user
quiz_sessions = {}  # Store active quiz sessions by user

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🎉 Welcome to Quiz Bot!\nUse /createquiz to make a new quiz.")

@bot.message_handler(commands=['createquiz'])
def create_quiz(message):
    bot.send_message(message.chat.id, "✏️ Send me the *title* of your quiz.", parse_mode="Markdown")
    bot.register_next_step_handler(message, get_quiz_title)

def get_quiz_title(message):
    title = message.text
    user_id = message.chat.id
    quiz_id = str(uuid.uuid4())[:8]
    user_quizzes.setdefault(user_id, {})[quiz_id] = {
        'title': title,
        'questions': []
    }
    bot.send_message(user_id, "✅ Title saved! Now send your *first question*.", parse_mode="Markdown")
    bot.register_next_step_handler(message, lambda msg: get_question(msg, quiz_id))

def get_question(message, quiz_id):
    question = message.text
    chat_id = message.chat.id
    quiz = user_quizzes[chat_id][quiz_id]
    quiz['questions'].append({'q': question, 'options': [], 'correct': 0})
    bot.send_message(chat_id, "📝 Send 4 options. (Send one message with all options separated by commas)\nExample: Delhi, Mumbai, Kolkata, Chennai")
    bot.register_next_step_handler(message, lambda msg: get_options(msg, quiz_id))

def get_options(message, quiz_id):
    options = [opt.strip() for opt in message.text.split(',')]
    if len(options) != 4:
        bot.send_message(message.chat.id, "❌ Please send exactly 4 options.")
        return bot.register_next_step_handler(message, lambda msg: get_options(msg, quiz_id))
    
    chat_id = message.chat.id
    quiz = user_quizzes[chat_id][quiz_id]
    quiz['questions'][-1]['options'] = options
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for i, opt in enumerate(options):
        markup.add(KeyboardButton(f"{i+1}. {opt}"))
    bot.send_message(chat_id, "✅ Options saved! Now select the correct option number:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda msg: save_correct_answer(msg, quiz_id))

def save_correct_answer(message, quiz_id):
    try:
        selected = int(message.text.split('.')[0]) - 1
    except:
        bot.send_message(message.chat.id, "❌ Please select a valid option number.")
        return bot.register_next_step_handler(message, lambda msg: save_correct_answer(msg, quiz_id))
    
    chat_id = message.chat.id
    quiz = user_quizzes[chat_id][quiz_id]
    quiz['questions'][-1]['correct'] = selected
    bot.send_message(chat_id, "✅ Question added! Do you want to add another question? (yes/no)")
    bot.register_next_step_handler(message, lambda msg: add_more_questions(msg, quiz_id))

def add_more_questions(message, quiz_id):
    chat_id = message.chat.id
    if message.text.lower() == 'yes':
        bot.send_message(chat_id, "✏️ Send your next question.")
        bot.register_next_step_handler(message, lambda msg: get_question(msg, quiz_id))
    else:
        link = f"https://t.me/{bot.get_me().username}?start=play_{quiz_id}"
        bot.send_message(chat_id, f"🎉 Quiz complete! Share this link to play:\n{link}")

@bot.message_handler(commands=['myquizzes'])
def list_quizzes(message):
    chat_id = message.chat.id
    quizzes = user_quizzes.get(chat_id, {})
    if not quizzes:
        return bot.send_message(chat_id, "😔 You haven't created any quizzes yet.")
    
    msg = "📝 Your Quizzes:\n"
    for qid, q in quizzes.items():
        link = f"https://t.me/{bot.get_me().username}?start=play_{qid}"
        msg += f"📌 {q['title']} - [Play Link]({link})\n"
    bot.send_message(chat_id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text.startswith('/start play_'))
def handle_play_link(message):
    quiz_id = message.text.split('_')[-1]
    for user_id, quizzes in user_quizzes.items():
        if quiz_id in quizzes:
            quiz = quizzes[quiz_id]
            quiz_sessions[message.chat.id] = {'quiz': quiz, 'index': 0, 'score': 0}
            return send_quiz_question(message.chat.id)
    bot.send_message(message.chat.id, "❌ Quiz not found.")

def send_quiz_question(chat_id):
    session = quiz_sessions[chat_id]
    index = session['index']
    quiz = session['quiz']
    if index >= len(quiz['questions']):
        score = session['score']
        total = len(quiz['questions'])
        del quiz_sessions[chat_id]
        return bot.send_message(chat_id, f"🎉 Quiz Complete!\nYour Score: {score}/{total}")
    
    q = quiz['questions'][index]
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for opt in q['options']:
        markup.add(KeyboardButton(opt))
    bot.send_message(chat_id, f"❓ Q{index+1}: {q['q']}", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.chat.id in quiz_sessions)
def handle_quiz_answer(message):
    session = quiz_sessions[message.chat.id]
    q = session['quiz']['questions'][session['index']]
    if message.text == q['options'][q['correct']]:
        session['score'] += 1
        bot.send_message(message.chat.id, "✅ Correct!")
    else:
        bot.send_message(message.chat.id, f"❌ Wrong! Correct answer: {q['options'][q['correct']]}")
    session['index'] += 1
    send_quiz_question(message.chat.id)

bot.polling()

