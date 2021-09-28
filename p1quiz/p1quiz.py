#! /usr/bin/python3

import tkinter as tk
import tkinter.font as tkfont
from tkinter import Tk, Label, Text, Button, Frame
import random
import time
import os

from PIL import ImageTk, Image

## Written in haste and there are parts in here that really need to
## be rewritten and some that are hardwired. Beware!     /Per

MAXWRONG = 3
ONLY_ONE_TRY = False

def dprint(s):
    # print(s)
    pass

def read_questions(fn):
    result = set()
    defaulttags = None
    difficulty = 0
    with open(fn) as f:
        for line in f:
            line = line.rstrip()
            if line.startswith('@q '):
                q = Question(line[3:])
                if defaulttags:
                    q.tags = defaulttags.copy()
                q.time = difficulty
                result.add(q)
            elif line.startswith('@diff '):
                difficulty = int(line[6:])
            elif line.startswith('@t '):
                q.tags.append(line[3:])
            elif line.startswith('@dt '):
                defaulttags = line[4:].split()
            elif line.startswith('@a '):
                q.answer = line[3:]
            elif line == '' or line.startswith('#'):
                pass
            elif line.startswith('@img '):
                q.image = line[5:]
            elif line.startswith('@py '):
                q.image = line[4:] + '.png'
            elif line.startswith('['):
                stop = line.index(']')
                score = int(line[1:stop])
                a = Wrong(line[stop+1:].strip())
                a.score = score
                q.wrong.append(a)
            else:
                q.wrong.append(Wrong(line))
    return result

class Question():
    def __init__(self, text):
        self.time = 0           # when last asked
        self.wrong = []
        self.tags = []
        self.image = None
        self.text = text
    def __repr__(self):
        return '<Q:{}>'.format(self.text)

# Wrong answers
class Wrong():
    def __init__(self, text):
        self.text = text
        self.score = 10          # higher score = tend to choose this

    def __repr__(self):
        return '<A [{}] {}>'.format(
            self.score, self.text)

# An alternative to choose from
def Alt():
    def __init__(self, button, correct=False):
        self.wrong = None
        

# Often choose the thing with highest priority, but not always
def choose_from_beginning(choices):
    li = choices.copy()
    # dprint('> choose_from_beginning({})'.format(li))
    while len(li) > 1 and random.random() < 0.3:
        li.pop(0)
    return li[0]

def mysortkey(x):
    s = x[0]
    s = s.replace('[', '')      # to sort ['foo'] and 'foo' close to each other
    if s.lower() == 'yes':
        return '0000'           # sort 'yes' before 'no'
    elif s.lower() == 'no':
        return '0001'
    else:
        return expandnumbers(s, 4)

def fixchar(c):
    if c == '−':                # minus sign
        return '-'              # ascii hyphen
    else:
        return c

def expandnumbers(s, n):
    digits = '0123456789'
    answer = ''
    ack = ''
    for c in s + ':': # stop character that isn't digit; later removed
        if c in digits:
            ack += c
        else:
            if ack:
                answer += '0'*(n-len(ack)) + ack
                ack = ''
            answer += fixchar(c)
    return answer[:-1]


# <> around code
def fragmentize(text):
    fragments = []
    current = []
    style = None
    for c in text:
        if c == '<':
            if current:
                fragments.append((''.join(current), style))
                current = []
            style = 'mono'
        elif c == '>':
            fragments.append((''.join(current), style))
            current = []
            style = None
        else:
            current.append(c)
    if current:
        fragments.append((''.join(current), style))
    return fragments

class GUI(Tk):
    def __init__(self, master=None):
        super().__init__(master)
        # self.pack()
        self.padx = self.pady = 5
        self.font = tkfont.Font(family='libertinus', size=12, weight='normal')
        self.title('Quiz')
        self.done = False
        self.answered = set()   # alternatives that already have been answered
        # self.geometry('1000x300')

    def ask(self):
        q = self.quiz.choose_question()
        if not q:
            self.done = True
            self.title('Completed Quiz')
            self.option_add("*background", '#ddffdd')
            q = self.contq
        is_same = (quiz.lastq == q)
        self.lastq = q
        self.answered = set()
        self.frame = Frame(self)
        self.frame.pack()
        if q.image:
            img = ImageTk.PhotoImage(Image.open(q.image))
            self.panel = Label(self.frame, image=img)
            # keep reference to image
            # http://effbot.org/pyfaq/why-do-my-tkinter-images-not-appear.htm
            self.img = img
            # self.panel.pack()
            # self.panel.pack(padx=self.padx, pady=self.pady, side=tk.LEFT)
            self.panel.grid(row=5, column=0)

        width = 55
        height = len(q.text)//width + 1
        # but word wrap will add some characters per line
        height = (len(q.text) + 5 * height) // width + 1
        self.text = Text(self.frame, font=self.font)
        self.text.config(height=height, width=width, padx=self.padx, pady=self.pady, wrap=tk.WORD)

        # self.text.insert(tk.END,'\n')
        self.text.grid(row=10, column=0)
        self.text.tag_config(tagName='mono', font="TkFixedFont")
        # self.text.insert(tk.END, q.text)
        for fragment, style in fragmentize(q.text):
            if style:
                self.text.insert(tk.END, fragment, style)
            else:
                self.text.insert(tk.END, fragment)
        self.text.config(state= tk.DISABLED)
        self.buttons = []
        self.answerframe = Frame(self.frame)
        self.answerframe.grid(row=20)
        if len(q.wrong) <= MAXWRONG:
            answers = [(a.text, a) for a in q.wrong]
            self.quiz.alts = q.wrong
        else:
            # answers = [(a.text, False) for a in choose_alts(q.wrong, MAXWRONG)]
            alts = choose_alts(q.wrong, MAXWRONG)
            self.quiz.alts = alts
            # text + wrong_answer
            # answers = [('{} [{}]'.format(a.text, a.score), a) for a in alts]
            answers = [(a.text, a) for a in alts]
        # "wrong_answer" is None when it isn't wrong
        answers.append((q.answer, None))
        answers.sort(key=mysortkey)

        for (text, wrong) in answers:
            if text[0] == ';':
                text = text[1:]
                style = 'mono'
            else:
                style = 'None'
            b = Button(self.answerframe, text=text,
                       bg="plum1", activebackground='orchid1',
                       padx=self.padx, pady=self.pady)
            if style == 'mono':
                b['font'] = 'TkFixedFont'
            if self.done:
                b.config(command=self.click_for_more(wrong))
            else:
                b.config(command=self.click(b, q, wrong))
            if not wrong:
                self.goodbutton = b
            self.buttons.append(b)
            # b.grid(row=0, column=bi)
            b.pack(padx=self.padx, pady=self.pady, side=tk.LEFT)


    def click_for_more(self, cont):
        def f():
            if cont:
                for goal in self.quiz.goal:
                    if goal in self.quiz.goalstart:
                        self.quiz.goal[goal] += self.quiz.goalstart[goal]
                    if goal in self.quiz.goaleachstart:
                        self.quiz.goaleach[goal] += self.quiz.goaleachstart[goal]
                self.done = False
                self.frame.destroy()
                self.ask()
            else:
                self.destroy()
        return f

    def click(self, button, question, wronganswer):
        def f():
            done = False
            diff = 0
            if not wronganswer:
                for alt in quiz.alts:
                    alt.score -= 1
                if not self.answered:
                    diff = -1
                button.configure(activebackground='green')
                button.update()
                self.after(200)
                done = True
            else:
                wronganswer.score += 5
                if not self.answered:
                    diff = 1
                button.configure(activebackground='red')
                if ONLY_ONE_TRY or self.answered or self.done:
                    self.goodbutton.configure(background='green')
                    button.update()
                    self.after(800)
                    done = True
                else:
                    button.update()
                    self.after(200)
                    button.configure(state="disabled")
                    self.answered.add(button)
            if done:
                for t in question.tags:
                    if t in quiz.goal:
                        quiz.goal[t] += diff
                self.frame.destroy()
                self.ask()
            else:
                again = Text(self.frame, font=self.font)
                again.config(height=1, width=55, padx=self.padx, pady=self.pady)
                again.insert(tk.END, "Sorry – try again!")
                again.config(state = tk.DISABLED)
                again.grid(row=100, column=0)
        return f

def choose_alts(alts, n):
    s = alts.copy()
    random.shuffle(s)
    s.sort(key=lambda a:a.score, reverse=True)
    res = []
    for _ in range(n):
        chosen = choose_from_beginning(s)
        s.remove(chosen)
        res.append(chosen)
    return res

class Quiz():
    def __init__(self, fn=None):
        self.goalstart = {}
        self.goaleachstart = {}
        self.goal = {}
        self.goaleach = {}
        self.moreinc = 2
        if fn:
            with open(fn) as f:
                for line in f:
                    words = line.split()
                    if words:
                        if words[0] == 'goal':
                            self.goal[words[1]] = int(words[2])
                            self.goalstart[words[1]] = int(words[2])
                        elif words[0] == 'goaleach':
                            self.goaleach[words[1]] = int(words[2])
                            self.goaleachstart[words[1]] = int(words[2])
        self.counter = self.counterstart = 10
        self.lastq = None

    def tick(self):
        # now and then increase the target for a goal, so old questions
        # can come back
        self.counter -= 1
        if self.counter <= 0:
            self.counter = self.counterstart
            self.goal[random.choice(list(self.goal))] += 1

    def choose_questions(self, qs):
        ans = []
        new_goals = {}
        for q in qs:
            include = True
            for t in q.tags.copy():
                if t not in self.goaleach and t not in self.goal:
                    include = False
                elif t in self.goaleach:
                    spectag = '{}-{}'.format(t, id(q))
                    new_goals[spectag] = self.goaleach[t]
                    q.tags.append(spectag)
            if include:
                ans.append(q)
        for (a,v) in new_goals.items():
            self.goal[a] = v
        dprint("Found questions {}".format(ans))
        return ans

    def choose_question(self):
        done = False
        # first find a list of candidates where at least one question
        # is different from the last question, so we don't have to repeat that
        while not done:
            self.tick()
            tags = []
            for t in self.goal:
                if self.goal[t] > 0:
                    tags.append(t)
            dprint('Sum is {}'.format(sum([self.goal[t] for t in tags])))
            candidates = set()
            if tags:
                for q in self.questions:
                    for tag in tags:
                        if tag in q.tags:
                            candidates.add(q)
            if candidates:
                candidates = list(candidates)
                if len(candidates) == 1 and candidates[0] == quiz.lastq:
                    pass
                    dprint('repeat...')
                else:
                    done = True
                    dprint('Choosing from {} candidates.'.format(len(candidates)))
            else:
                done = True
        # then choose one of them
        if candidates:
            if quiz.lastq in candidates:
                candidates.remove(quiz.lastq)
            candidates.sort(key=lambda q:q.time)
            c = choose_from_beginning(candidates)
            c.time = time.time()
            return c
        else:
            return None

# quiz = None

def main():
    global gui, quiz
    gui = GUI()
    #os.chdir("/local/lib/quiz/p1")
    quiz = Quiz('p1.quiz')
    qs = read_questions('p1.qs')
    # quiz = Quiz('us.quiz')
    # qs = read_questions('us.qs')
    quiz.questions = quiz.choose_questions(qs)
    gui.quizzes = [quiz]
    gui.quiz = quiz

    contq = Question('That’s good! Do you want to train some more?')
    contq.answer = 'No'         # "correct" answer, because then you are done
    contq.wrong = [Wrong('Yes')]
    gui.contq = contq

    gui.monofont = tkfont.Font(family='beramono', size=12)

    gui.ask()
    gui.mainloop()

if __name__ == "__main__":
    main()
