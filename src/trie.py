from src.start_seq import StartSequence
from src.trie_node import TrieNode
from src.scorer import Scorer
from src.coord import Coord

class Trie:
    def __init__(self):
        self.root = TrieNode()
        self.scorer = Scorer()

    def insert(self, s):
        self.insert_helper(self.root, s, 0)

    def insert_helper(self, node, s, i):
        if i == len(s):
            node.is_word = True
        else:
            curletter = s[i]
            if curletter not in node.children:
                node.children[curletter] = TrieNode()
            self.insert_helper(node.children[curletter], s, i + 1)

    def contains(self, s):
        return self.contains_helper(self.root, s)

    def contains_helper(self, node, s):
        if s == "":
            return node.is_word
        curletter = s[0]
        if curletter in node.children:
            return self.contains_helper(node.children[curletter], s[1:])
        else:
            return False

    # return a StartSequence that includes the word template
    def get_plays_constrained(self, start_seq, tiles, board, dist):
        templates = self.get_words_constrained(start_seq, tiles, board)

        plays = []
        x, y = start_seq.x, start_seq.y
        ish = start_seq.ish
        for template in templates:
            if not all(c is None for c in template) and len(template) >= dist:
                play = StartSequence(x, y, template, ish)
                score = self.score_play(play, board)
                play.points = score
                plays.append(play)
        return plays

    def get_words(self, template):
        return self.get_words_helper(template, self.root)

    def get_chars(self, template):
        # check that there is only one None in the template; error if > 1
        from functools import reduce
        num_blanks = reduce((lambda n, c: n + int(not c)), template, 0)
        if num_blanks != 1:
            raise RuntimeError(f"Template should have 1 blank. {num_blanks} blanks.")
        return self.get_chars_helper(template, self.root)

    def get_words_constrained(self, start_seq, tiles, board):
        s_list = []
        self.get_words_constrained_helper(start_seq, self.root, tiles, board, s_list)
        return s_list

    def get_words_helper(self, template, node, s = ""):
        # while we still have spaces left to fill
        if template != []:
            curspot = template[0]
            if curspot:
                child_words = []
                if curspot in node.children:
                    temps = s + curspot
                    child_words = self.get_words_helper(template[1:],
                        node.children[curspot], temps)
                return child_words
            else:
                words = []
                for next in node.children:
                    temps = s + next
                    child_words = self.get_words_helper(template[1:],
                        node.children[next], temps)
                    if child_words:
                        words.extend(child_words)
                return words
        else:
            if node.is_word:
                return [s]

    # get possible characters for first blank
    def get_chars_helper(self, template, node, c = ""):
        # while we still have spaces left to fill
        if template != []:
            curspot = template[0]
            if curspot:
                child_words = []
                if curspot in node.children:
                    child_words = self.get_chars_helper(template[1:],
                        node.children[curspot], c)
                return child_words
            else:
                chars = []
                for next in node.children:
                    child_words = self.get_chars_helper(template[1:],
                        node.children[next], next)
                    if child_words:
                        chars.extend(child_words)
                return chars
        else:
            if node.is_word:
                return [c]

    def get_words_constrained_helper(self, start_seq, node, tiles, board, s_list, s = []):
        curX, curY = start_seq.x, start_seq.y
        template = start_seq.template
        ish = start_seq.ish

        if template != []:
            curspot = template[0]
            if curspot:
                if curspot in node.children:
                    temps = s + [None]
                    if ish:
                        temp_start_seq = StartSequence(curX + 1, curY, template[1:], ish)
                    else:
                        temp_start_seq = StartSequence(curX, curY + 1, template[1:], ish)
                    child_words = self.get_words_constrained_helper(temp_start_seq,
                        node.children[curspot], tiles, board, s_list, temps)
            else:
                if node.is_word:
                    s_list.append(s)
                crosscheck = board.crosschecks[curY][curX].v_check if ish else board.crosschecks[curY][curX].h_check
                to_traverse = list(crosscheck.intersection(set(tiles)))

                for next in to_traverse:
                    if next in node.children:
                        temps = s + [next]
                        if ish:
                            temp_start_seq = StartSequence(curX + 1, curY, template[1:], ish)
                        else:
                            temp_start_seq = StartSequence(curX, curY + 1 , template[1:], ish)
                        remaining_tiles = tiles[:]
                        remaining_tiles.remove(next)
                        self.get_words_constrained_helper(temp_start_seq,
                            node.children[next], remaining_tiles, board, s_list, temps)
        else:
            if node.is_word:
                s_list.append(s)

    def score_play(self, play, board):
        x, y = play.x, play.y
        ish = play.ish
        template = play.template
        dX, dY = (1, 0) if ish else (0, 1)
        mult_score = 0
        base_score = 0
        factor = 1
        for c in template:
            if not c:
                mult_score += self.scorer.get_score_old(board.tiles[y][x])
            else:
                square_score, square_factor = self.scorer.get_score_new(x, y, c)
                mult_score += square_score
                factor *= square_factor
                base_score += self.score_helper(Coord(x, y), board, ish)
            x += dX
            y += dY
        return (mult_score * factor) + base_score

    def score_helper(self, coord, board, ish):
        base_score = 0
        dX, dY = (0, 1) if ish else (1, 0)
        x, y = coord[0] - 1, coord[1] - 1
        while (x >= 0 and y >= 0) and board.tiles[y][x]:

            base_score += self.scorer.get_score_old(board.tiles[y][x])
            x -= dX
            y -= dY
        x, y = coord[0] + 1, coord[1] + 1
        while (x < board.size and y < board.size) and board.tiles[y][x]:
            base_score += self.scorer.get_score_old(board.tiles[y][x])
            x += dX
            y += dY
        return base_score

    scrabble_words = None

    @staticmethod
    def words():
        if Trie.scrabble_words is None:
            with open("assets/scrabble_dictionary.txt") as f:
                words = f.read().lower().splitlines()
            Trie.scrabble_words = Trie()
            for word in words:
                Trie.scrabble_words.insert(word)
        return Trie.scrabble_words
