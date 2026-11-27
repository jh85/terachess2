import Rules

open Terachess

-- Transport for differential tests. The Python harness converts FEN to this square-indexed format.
def pieceKinds : Array Kind :=
  #[.amazon, .bishop, .cannon, .duchess, .elephant, .buffalo, .eagle, .marshall,
    .prince, .centaur, .king, .lion, .camel, .knight, .sorceress, .pawn, .queen,
    .rook, .admiral, .troll, .rhinoceros, .archer, .machine, .cardinal, .missionary, .giraffe]

def readPiece (c : Char) : Option Piece :=
  if c = '.' then none
  else (pieceKinds[c.toLower.toNat - 'a'.toNat]?).map fun k =>
    ⟨if c.isUpper then .white else .black, k⟩

def writePiece : Option Piece → Char
  | none => '.'
  | some p =>
    let i := pieceKinds.toList.idxOf p.kind
    Char.ofNat (i + if p.side = .white then 'A'.toNat else 'a'.toNat)

def sq (n : Nat) : Square := (Fin.ofNat' 16 (n % 16), Fin.ofNat' 16 (n / 16))
def index (q : Square) : Nat := q.2.val * 16 + q.1.val
def code (m : Move) : Nat := index m.src * 256 + index m.dst

def readLine (line : String) : Option (Position × Option Move) := do
  let [cells, side, jumps, ep, half, full, move] := line.trim.splitOn " " | none
  let board := cells.toList.toArray.map readPiece
  let king := fun side => squares.find? fun q => board[index q]! == some ⟨side, .king⟩
  let white ← king .white
  let black ← king .black
  let rights ← jumps.toNat?
  let halfmove ← half.toNat?
  let fullmove ← full.toNat?
  let num := move.toNat?
  let m := num.map fun c => Move.mk (sq (c / 256)) (sq (c % 256))
  return (⟨(fun q => board[index q]!), if side == "w" then .white else .black,
           (fun s => if s == .white then white else black),
           (fun s => if s == .white then rights % 2 == 1 else rights / 2 == 1),
           ep.toNat?.map sq, halfmove, fullmove⟩, m)

def writePosition (p : Position) : String :=
  let board := String.mk (squares.map fun q => writePiece (p.board q))
  let rights : Nat := (if p.jump .white then 1 else 0) + (if p.jump .black then 2 else 0)
  let ep := match p.ep with | none => "-" | some q => toString (index q)
  " ".intercalate [board, if p.turn == .white then "w" else "b",
                    toString rights, ep, toString p.halfmove, toString p.fullmove]

def main : IO Unit := do
  let input ← IO.getStdin
  let output ← IO.getStdout
  output.putStrLn (writePosition initial)
  repeat
    let line ← input.getLine
    if line.isEmpty then break
    let some (p, m) := readLine line | throw (IO.userError "invalid test input")
    let moves := String.intercalate "," ((legalMoves p).map (toString ∘ code))
    let next := ((m.bind (step p)).map writePosition).getD "-"
    output.putStrLn (moves ++ "|" ++ next)
