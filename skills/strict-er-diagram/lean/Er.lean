/-
  strict-er-diagram: 型付きモデル、正規JSON、投影、Mermaid/SVG の生成と限定読取、幾何検査。
  全関数は構造的再帰のみ。カーネルで評価する値に String を使わず Bytes (長さ, 256進Nat) を使う。
-/
namespace Er

structure Bytes where
  n : Nat
  v : Nat
  deriving DecidableEq, Repr

macro:max "b!" s:str : term => do
  let bs := s.getString.toUTF8
  let v := bs.foldl (fun acc b => acc * 256 + b.toNat) 0
  `(Bytes.mk $(Lean.Syntax.mkNumLit (toString bs.size)) $(Lean.Syntax.mkNumLit (toString v)))

/-- 読取で比較する定数。展開済みのリストにしてカーネルの算術を省く -/
macro:max "k!" s:str : term => do
  let items : Array Lean.Term := s.getString.toUTF8.data.map fun x =>
    (⟨Lean.Syntax.mkNumLit (toString x.toNat)⟩ : Lean.Term)
  `([$items,*])

macro:max "c!" s:str : term => do
  let bs := s.getString.toUTF8
  `($(Lean.Syntax.mkNumLit (toString (bs.get! 0).toNat)))

def Bytes.nil : Bytes := ⟨0, 0⟩
@[inline] def Bytes.app (a b : Bytes) : Bytes := ⟨a.n + b.n, a.v * 256 ^ b.n + b.v⟩
instance : Append Bytes := ⟨Bytes.app⟩

def Bytes.toList (s : Bytes) : List Nat :=
  let rec go : Nat → List Nat
    | 0 => []
    | k + 1 => (s.v / 256 ^ k % 256) :: go k
  go s.n

def ofList (l : List Nat) : Bytes := l.foldl (fun a c => ⟨a.n + 1, a.v * 256 + c⟩) Bytes.nil

def concat : List Bytes → Bytes
  | [] => Bytes.nil
  | a :: t => a ++ concat t

def joinLines : List Bytes → Bytes
  | [] => Bytes.nil
  | a :: t => a ++ b!"\n" ++ joinLines t

def sepBy (sep : Bytes) : List Bytes → Bytes
  | [] => Bytes.nil
  | [a] => a
  | a :: t => a ++ sep ++ sepBy sep t

def digits : Nat → Nat → List Nat → List Nat
  | 0, _, acc => acc
  | f + 1, n, acc => if n < 10 then (48 + n) :: acc else digits f (n / 10) ((48 + n % 10) :: acc)

def natB (n : Nat) : Bytes := ofList (digits 12 n [])

/-! ## モデル -/

inductive Mult | zeroOne | one | zeroMany | oneMany | unknown deriving DecidableEq, Repr
inductive Line | solid | dashed deriving DecidableEq, Repr
inductive Notation | crows | chen | ratio | unknown deriving DecidableEq, Repr
inductive LineSem | identifying | none | unknown deriving DecidableEq, Repr
inductive View | conceptual | logical deriving DecidableEq, Repr

structure Attr where
  id : Bytes
  name : Bytes
  ty : Option Bytes
  pk : Bool
  fk : Bool
  uk : Bool
  note : Option Bytes
  deriving DecidableEq, Repr

structure Ent where
  id : Bytes
  name : Bytes
  attrs : List Attr
  deriving DecidableEq, Repr

structure Rel where
  id : Bytes
  src : Bytes
  dst : Bytes
  sm : Mult
  dm : Mult
  line : Line
  identifying : Option Bool
  label : Option Bytes
  deriving DecidableEq, Repr

structure Unres where
  target : Bytes
  field : Bytes
  conceptual : Bool
  logical : Bool
  question : Bytes
  deriving DecidableEq, Repr

structure Model where
  nota : Notation
  lineSem : LineSem
  ents : List Ent
  rels : List Rel
  unresolved : List Unres
  deriving DecidableEq, Repr

/-! ## 正規JSON -/

def escByte (c : Nat) : List Nat :=
  if c == 34 then [92, 34]
  else if c == 92 then [92, 92]
  else if c < 32 then
    let hex (d : Nat) := if d < 10 then 48 + d else 87 + d
    [92, 117, 48, 48, hex (c / 16), hex (c % 16)]
  else [c]

def jstr (s : Bytes) : Bytes :=
  b!"\"" ++ ofList (s.toList.flatMap escByte) ++ b!"\""

def jopt (s : Option Bytes) : Bytes :=
  match s with | some x => jstr x | none => b!"null"

def jbool (b : Bool) : Bytes := if b then b!"true" else b!"false"

def jarr (l : List Bytes) : Bytes := b!"[" ++ sepBy b!"," l ++ b!"]"

def multName : Mult → Bytes
  | .zeroOne => b!"zero_or_one" | .one => b!"exactly_one"
  | .zeroMany => b!"zero_or_more" | .oneMany => b!"one_or_more" | .unknown => b!"unknown"

def lineName : Line → Bytes | .solid => b!"solid" | .dashed => b!"dashed"
def notationName : Notation → Bytes
  | .crows => b!"crows_foot" | .chen => b!"chen" | .ratio => b!"ratio" | .unknown => b!"unknown"
def lineSemName : LineSem → Bytes
  | .identifying => b!"identifying" | .none => b!"none" | .unknown => b!"unknown"

def keysOf (a : Attr) : List Bytes :=
  (if a.pk then [b!"PK"] else []) ++ (if a.fk then [b!"FK"] else []) ++ (if a.uk then [b!"UK"] else [])

def encAttr (a : Attr) : Bytes :=
  b!"{\"id\":" ++ jstr a.id ++ b!",\"keys\":" ++ jarr ((keysOf a).map jstr)
    ++ b!",\"name\":" ++ jstr a.name ++ b!",\"note\":" ++ jopt a.note
    ++ b!",\"type\":" ++ jopt a.ty ++ b!"}"

def encEnt (e : Ent) : Bytes :=
  b!"{\"attributes\":" ++ jarr (e.attrs.map encAttr) ++ b!",\"id\":" ++ jstr e.id
    ++ b!",\"name\":" ++ jstr e.name ++ b!"}"

def encRel (r : Rel) : Bytes :=
  b!"{\"dst\":" ++ jstr r.dst ++ b!",\"dst_multiplicity\":" ++ jstr (multName r.dm)
    ++ b!",\"id\":" ++ jstr r.id
    ++ b!",\"identifying\":" ++ (match r.identifying with | some x => jbool x | none => b!"null")
    ++ b!",\"label\":" ++ jopt r.label ++ b!",\"line_style\":" ++ jstr (lineName r.line)
    ++ b!",\"src\":" ++ jstr r.src ++ b!",\"src_multiplicity\":" ++ jstr (multName r.sm) ++ b!"}"

def encUnres (u : Unres) : Bytes :=
  b!"{\"field\":" ++ jstr u.field ++ b!",\"question\":" ++ jstr u.question
    ++ b!",\"target\":" ++ jstr u.target ++ b!",\"views\":"
    ++ jarr ((if u.conceptual then [jstr b!"conceptual"] else [])
      ++ (if u.logical then [jstr b!"logical"] else [])) ++ b!"}"

def encodeDsl (m : Model) : Bytes :=
  b!"{\"entities\":" ++ jarr (m.ents.map encEnt)
    ++ b!",\"line_semantics\":" ++ jstr (lineSemName m.lineSem)
    ++ b!",\"notation\":" ++ jstr (notationName m.nota)
    ++ b!",\"relationships\":" ++ jarr (m.rels.map encRel)
    ++ b!",\"schema_version\":1,\"unresolved\":" ++ jarr (m.unresolved.map encUnres) ++ b!"}\n"

/-! ## 整形式性と図ごとの状態 -/

def memB (x : Bytes) : List Bytes → Bool
  | [] => false
  | a :: t => a == x || memB x t

def distinct : List Bytes → Bool
  | [] => true
  | a :: t => !memB a t && distinct t

def isIdChar (c : Nat) : Bool :=
  (48 ≤ c && c ≤ 57) || (65 ≤ c && c ≤ 90) || (97 ≤ c && c ≤ 122) || c == 95

def validId (s : Bytes) : Bool := 0 < s.n && s.toList.all isIdChar

def attrsOf (m : Model) : List Attr := m.ents.flatMap (·.attrs)

def identConsistent (m : Model) (r : Rel) : Bool :=
  match m.lineSem, r.identifying, r.line with
  | .identifying, some true, .solid => true
  | .identifying, some false, .dashed => true
  | .identifying, _, _ => false
  | _, none, _ => true
  | _, _, _ => false

def unknownCovered (m : Model) (r : Rel) (field : Bytes) : Bool :=
  m.unresolved.any fun u => u.target == r.id && u.field == field && u.conceptual && u.logical

def multCovered (m : Model) (r : Rel) : Bool :=
  (r.sm != .unknown || unknownCovered m r b!"src_multiplicity")
    && (r.dm != .unknown || unknownCovered m r b!"dst_multiplicity")

def wellFormed (m : Model) : Bool :=
  let eids := m.ents.map (·.id)
  let aids := (attrsOf m).map (·.id)
  let rids := m.rels.map (·.id)
  distinct eids && distinct aids && distinct rids
    && eids.all validId && aids.all validId && rids.all validId
    && m.rels.all (fun r => memB r.src eids && memB r.dst eids
        && identConsistent m r && multCovered m r)
    && m.ents.all (fun e => 0 < e.name.n)
    && (attrsOf m).all (fun a => 0 < a.name.n)
    && m.unresolved.all (fun u => (u.conceptual || u.logical)
        && (memB u.target eids || memB u.target aids || memB u.target rids || u.target == b!"diagram"))

inductive Status | ready | draft | blocked deriving DecidableEq, Repr

structure Classified where
  status : Status
  missing : List Bytes
  deriving DecidableEq, Repr

def forView (v : View) (u : Unres) : Bool :=
  match v with | .conceptual => u.conceptual | .logical => u.logical

def missingLogical (m : Model) : List Bytes :=
  m.ents.flatMap fun e =>
    (if e.attrs.isEmpty then [e.id ++ b!".attributes"] else [])
      ++ (if e.attrs.any (·.pk) then [] else [e.id ++ b!".identifier"])

def missingCommon (m : Model) : List Bytes :=
  (match m.lineSem with | .unknown => [b!"diagram.line_semantics"] | _ => [])
    ++ (match m.nota with | .unknown => [b!"diagram.nota"] | _ => [])

def classifyView (v : View) (m : Model) : Classified :=
  let open_ := m.unresolved.filter (forView v)
  let blockers := open_.map (fun u => u.target ++ b!"." ++ u.field)
  let missing := missingCommon m ++ (match v with | .logical => missingLogical m | .conceptual => [])
  if !blockers.isEmpty then ⟨.blocked, blockers ++ missing⟩
  else if !missing.isEmpty then ⟨.draft, missing⟩
  else ⟨.ready, []⟩

def statusName : Status → Bytes
  | .ready => b!"ready" | .draft => b!"draft" | .blocked => b!"blocked"

def encodeClassified (c : Classified) : Bytes :=
  b!"{\"missing\":" ++ jarr (c.missing.map jstr) ++ b!",\"status\":" ++ jstr (statusName c.status)
    ++ b!"}\n"

/-! ## 投影（意味モデル） -/

structure PAttr where
  name : Bytes
  ty : Option Bytes
  pk : Bool
  fk : Bool
  uk : Bool
  note : Option Bytes
  deriving DecidableEq, Repr

structure PEnt where
  id : Bytes
  name : Bytes
  attrs : List PAttr
  deriving DecidableEq, Repr

structure PRel where
  src : Bytes
  dst : Bytes
  sm : Mult
  dm : Mult
  line : Line
  label : Option Bytes
  deriving DecidableEq, Repr

structure PModel where
  ents : List PEnt
  rels : List PRel
  deriving DecidableEq, Repr

def project (v : View) (m : Model) : PModel :=
  ⟨m.ents.map (fun e => ⟨e.id, e.name, match v with
      | .conceptual => []
      | .logical => e.attrs.map fun a => ⟨a.name, a.ty, a.pk, a.fk, a.uk, a.note⟩⟩),
   m.rels.map fun r => ⟨r.src, r.dst, r.sm, r.dm, r.line, r.label⟩⟩

/-! ## Mermaid -/

def leftSym : Mult → Bytes
  | .zeroOne => b!"|o" | .one => b!"||" | .zeroMany => b!"}o" | .oneMany => b!"}|" | .unknown => b!"??"
def rightSym : Mult → Bytes
  | .zeroOne => b!"o|" | .one => b!"||" | .zeroMany => b!"o\x7b" | .oneMany => b!"|\x7b"
  | .unknown => b!"??"

def keyList (a : PAttr) : List Bytes :=
  (if a.pk then [b!"PK"] else []) ++ (if a.fk then [b!"FK"] else []) ++ (if a.uk then [b!"UK"] else [])

def mmdAttr (a : PAttr) : Bytes :=
  b!"    " ++ (a.ty.getD b!"unknown") ++ b!" " ++ a.name
    ++ (match keyList a with | [] => Bytes.nil | ks => b!" " ++ sepBy b!", " ks)
    ++ (match a.note with | some x => b!" \"" ++ x ++ b!"\"" | none => Bytes.nil) ++ b!"\n"

def mmdEnt (e : PEnt) : Bytes :=
  b!"  " ++ e.id ++ b!"[\"" ++ e.name ++ b!"\"]"
    ++ (if e.attrs.isEmpty then b!"\n"
        else b!" \x7b\n" ++ concat (e.attrs.map mmdAttr) ++ b!"  \x7d\n")

def mmdRel (r : PRel) : Bytes :=
  b!"  " ++ r.src ++ b!" " ++ leftSym r.sm ++ (match r.line with | .solid => b!"--" | .dashed => b!"..")
    ++ rightSym r.dm ++ b!" " ++ r.dst ++ b!" : \"" ++ r.label.getD Bytes.nil ++ b!"\"\n"

def renderMermaid (p : PModel) : Bytes :=
  b!"erDiagram\n" ++ concat (p.ents.map mmdEnt) ++ concat (p.rels.map mmdRel)

def isDigit (c : Nat) : Bool := 48 ≤ c && c ≤ 57
def isAlpha (c : Nat) : Bool := (65 ≤ c && c ≤ 90) || (97 ≤ c && c ≤ 122)

/-- 属性名の許可: 英数字・_・-・非ASCII、先頭は数字以外 -/
def nameCharOk (c : Nat) : Bool := isAlpha c || isDigit c || c == 95 || c == 45 || 128 ≤ c
def tyCharOk (c : Nat) : Bool := nameCharOk c || c == 40 || c == 41 || c == 44 || c == 91 || c == 93

def headOk (l : List Nat) : Bool :=
  match l with | [] => false | c :: _ => !isDigit c && c != 45

def identOk (s : Bytes) : Bool := let l := s.toList; headOk l && l.all nameCharOk
def typeOk (s : Bytes) : Bool :=
  let l := s.toList; headOk l && l.all tyCharOk && s != b!"unknown"

/-- 引用文字列の許可: " # < > & と制御文字を含まない -/
def quotedOk (s : Bytes) : Bool :=
  s.toList.all fun c => 32 ≤ c && c != 34 && c != 35 && c != 60 && c != 62 && c != 38 && c != 127

def attrRepresentable (a : PAttr) : Bool :=
  identOk a.name && (match a.ty with | some t => typeOk t | none => true)
    && (match a.note with | some x => quotedOk x | none => true)

def relRepresentable (r : PRel) : Bool :=
  r.sm != .unknown && r.dm != .unknown
    && (match r.label with | some x => 0 < x.n && quotedOk x | none => true)

def mermaidProblems (p : PModel) : List Bytes :=
  (p.ents.flatMap fun e =>
    (if quotedOk e.name then [] else [e.id ++ b!".name"])
      ++ (e.attrs.flatMap fun a =>
        if attrRepresentable a then [] else [e.id ++ b!".attribute:" ++ a.name]))
  ++ (p.rels.flatMap fun r =>
    if relRepresentable r then [] else [r.src ++ b!"-" ++ r.dst ++ b!".relationship"])

def mermaidRepresentable (p : PModel) : Bool := (mermaidProblems p).isEmpty

/-! ### 限定読取の共通部品（生成関数を呼ばない） -/

def expect : List Nat → List Nat → Option (List Nat)
  | [], r => some r
  | _ :: _, [] => none
  | a :: t, b :: r => if a == b then expect t r else none

def lit (s : List Nat) (r : List Nat) : Option (List Nat) := expect s r

/-- 区切りバイトまで読む。区切りは消費する -/
def untilByte (d : Nat) : List Nat → Option (List Nat × List Nat)
  | [] => none
  | c :: t =>
    if c == d then some ([], t) else
    match untilByte d t with
    | some (a, r) => some (c :: a, r)
    | none => none

def spanWhile (p : Nat → Bool) : List Nat → List Nat × List Nat
  | [] => ([], [])
  | c :: t =>
    if p c then
      let (a, r) := spanWhile p t
      (c :: a, r)
    else ([], c :: t)

def parseMultL (l : List Nat) : Option (Mult × List Nat) :=
  match lit k!"|o" l with
  | some r => some (.zeroOne, r)
  | none => match lit k!"||" l with
    | some r => some (.one, r)
    | none => match lit k!"}o" l with
      | some r => some (.zeroMany, r)
      | none => match lit k!"}|" l with
        | some r => some (.oneMany, r)
        | none => none

def parseMultR (l : List Nat) : Option (Mult × List Nat) :=
  match lit k!"o|" l with
  | some r => some (.zeroOne, r)
  | none => match lit k!"||" l with
    | some r => some (.one, r)
    | none => match lit k!"o\x7b" l with
      | some r => some (.zeroMany, r)
      | none => match lit k!"|\x7b" l with
        | some r => some (.oneMany, r)
        | none => none

inductive MItem
  | entOpen (id name : Bytes)
  | entBare (id name : Bytes)
  | attr (a : PAttr)
  | close
  | rel (r : PRel)
  deriving DecidableEq

def parseKeys (l : List Nat) : Option (Bool × Bool × Bool × List Nat) :=
  -- l は「 PK, FK "note"」または「 "note"」または空
  match lit k!" " l with
  | none => if l.isEmpty then some (false, false, false, []) else none
  | some r0 =>
    let step (k : List Nat) (r : List Nat) : Bool × List Nat :=
      match lit k r with
      | some r' => (true, match lit k!", " r' with | some r'' => r'' | none => r')
      | none => (false, r)
    let (pk, r1) := step k!"PK" r0
    let (fk, r2) := step k!"FK" r1
    let (uk, r3) := step k!"UK" r2
    if pk || fk || uk then
      if r3.isEmpty then some (pk, fk, uk, [])
      else match lit k!" " r3 with
        | some r4 => some (pk, fk, uk, r4)
        | none => none
    else some (false, false, false, r0)

def parseAttr (l : List Nat) : Option MItem :=
  match lit k!"    " l with
  | none => none
  | some r =>
    match untilByte 32 r with
    | none => none
    | some (ty, r1) =>
      let (nm, r2) := spanWhile (· != 32) r1
      if nm.isEmpty then none else
      match parseKeys r2 with
      | none => none
      | some (pk, fk, uk, r3) =>
        let note : Option (Option Bytes) :=
          match r3 with
          | [] => some none
          | 34 :: q => match untilByte 34 q with
            | some (x, []) => some (some (ofList x))
            | _ => none
          | _ => none
        match note with
        | none => none
        | some nt =>
          let tyB := ofList ty
          some (.attr ⟨ofList nm, if tyB == b!"unknown" then none else some tyB, pk, fk, uk, nt⟩)

def parseRel (id : List Nat) (r : List Nat) : Option MItem :=
  match lit k!" " r with
  | none => none
  | some r1 =>
    match parseMultL r1 with
    | none => none
    | some (sm, r2) =>
      let ln : Option (Line × List Nat) :=
        match lit k!"--" r2 with
        | some r3 => some (.solid, r3)
        | none => match lit k!".." r2 with
          | some r3 => some (.dashed, r3)
          | none => none
      match ln with
      | none => none
      | some (line, r3) =>
        match parseMultR r3 with
        | none => none
        | some (dm, r4) =>
          match lit k!" " r4 with
          | none => none
          | some r5 =>
            match untilByte 32 r5 with
            | none => none
            | some (dst, r6) =>
              match lit k!": \"" r6 with
              | none => none
              | some r7 =>
                match untilByte 34 r7 with
                | some (lab, []) =>
                  some (.rel ⟨ofList id, ofList dst, sm, dm, line,
                    if lab.isEmpty then none else some (ofList lab)⟩)
                | _ => none

def parseMmdLine (line : Bytes) : Option MItem :=
  let l := line.toList
  if l == k!"  \x7d" then some .close else
  match lit k!"    " l with
  | some _ => parseAttr l
  | none =>
    match lit k!"  " l with
    | none => none
    | some r =>
      let (id, r1) := spanWhile isIdChar r
      if id.isEmpty then none else
      match lit k!"[\"" r1 with
      | some r2 =>
        match untilByte 34 r2 with
        | none => none
        | some (nm, r3) =>
          match lit k!"]" r3 with
          | none => none
          | some [] => some (.entBare (ofList id) (ofList nm))
          | some r4 =>
            match lit k!" \x7b" r4 with
            | some [] => some (.entOpen (ofList id) (ofList nm))
            | _ => none
      | none => parseRel id r1

structure MState where
  ents : List PEnt
  rels : List PRel
  pending : List PAttr
  inBlock : Bool

/-- 末尾から組み立てる。属性ブロックと「エンティティが関係より前」の順序を検査する -/
def assemble : List MItem → Option MState
  | [] => some ⟨[], [], [], false⟩
  | it :: t =>
    match assemble t with
    | none => none
    | some st =>
      match it with
      | .rel r =>
        if !st.ents.isEmpty || st.inBlock then none else some { st with rels := r :: st.rels }
      | .close => if st.inBlock then none else some { st with inBlock := true, pending := [] }
      | .attr a => if st.inBlock then some { st with pending := a :: st.pending } else none
      | .entOpen id nm =>
        if st.inBlock && !st.pending.isEmpty then
          some { st with ents := ⟨id, nm, st.pending⟩ :: st.ents, inBlock := false, pending := [] }
        else none
      | .entBare id nm =>
        if st.inBlock then none else some { st with ents := ⟨id, nm, []⟩ :: st.ents }

def mapOpt {α β} (f : α → Option β) : List α → Option (List β)
  | [] => some []
  | a :: t =>
    match f a with
    | none => none
    | some b => match mapOpt f t with
      | none => none
      | some r => some (b :: r)

def noNl (s : Bytes) : Bool := s.toList.all (· != 10)

/-- 保存物 saved を行 lines へ分けて読む。行分割はヒントで、join の一致で検査する -/
def decodeMermaidSubset (saved : Bytes) (lines : List Bytes) : Option PModel :=
  if joinLines lines != saved || !lines.all noNl then none else
  match lines with
  | [] => none
  | h :: t =>
    if h != b!"erDiagram" then none else
    match mapOpt parseMmdLine t with
    | none => none
    | some items =>
      match assemble items with
      | some st => if st.inBlock then none else some ⟨st.ents, st.rels⟩
      | none => none

/-! ## レイアウト（SVG） -/

structure Pt where
  x : Nat
  y : Nat
  deriving DecidableEq, Repr

inductive Side | bottom | top | right deriving DecidableEq, Repr

/-- UTF-8 の推定表示幅（13px）。ASCII 8px、それ以外 14px。実描画の幅は描画確認の対象 -/
def textW (s : Bytes) : Nat :=
  s.toList.foldl (fun w c => w + (if c < 128 then 8 else if 192 ≤ c then 14 else 0)) 0

def maxL (l : List Nat) : Nat := l.foldl max 0

def lookupN (k : Bytes) : List (Bytes × Nat) → Nat
  | [] => 0
  | (a, v) :: t => if a == k then v else lookupN k t

def isqrtCeil (n : Nat) : Nat :=
  let rec go : Nat → Nat → Nat
    | 0, c => c
    | f + 1, c => if n ≤ c * c then c else go f (c + 1)
  go n 1

/-- 接続のあるエンティティが隣り合うよう幅優先で並べる -/
def bfsOrder (p : PModel) : List Bytes :=
  let ids := p.ents.map (·.id)
  let nbrs (x : Bytes) : List Bytes :=
    p.rels.flatMap fun r => if r.src == x then [r.dst] else if r.dst == x then [r.src] else []
  let rec go : Nat → List Bytes → List Bytes → List Bytes
    | 0, _, seen => seen.reverse
    | f + 1, queue, seen =>
      match queue with
      | x :: q =>
        if memB x seen then go f q seen
        else go f (q ++ nbrs x) (x :: seen)
      | [] =>
        match ids.filter (fun i => !memB i seen) with
        | i :: _ => go f [i] seen
        | [] => seen.reverse
  go ((ids.length + 1) * (p.rels.length + 2) * 2) [] []

structure Cell where
  col : Nat
  row : Nat
  deriving DecidableEq, Repr

structure RelPlan where
  srcCell : Cell
  dstCell : Cell
  srcSide : Side
  dstSide : Side
  deriving Repr

def indexOfB (x : Bytes) : List Bytes → Nat
  | [] => 0
  | a :: t => if a == x then 0 else 1 + indexOfB x t

def planRel (order : List Bytes) (cols : Nat) (r : PRel) : RelPlan :=
  let i := indexOfB r.src order
  let j := indexOfB r.dst order
  let a : Cell := ⟨i % cols, i / cols⟩
  let b : Cell := ⟨j % cols, j / cols⟩
  if i == j then ⟨a, b, .right, .right⟩
  else if a.row == b.row then ⟨a, b, .bottom, .bottom⟩
  else if a.row < b.row then ⟨a, b, .bottom, .top⟩
  else ⟨a, b, .top, .bottom⟩

def sideKey (cols : Nat) (c : Cell) (s : Side) : Nat :=
  (c.row * cols + c.col) * 3 + (match s with | .bottom => 0 | .top => 1 | .right => 2)

/-- 連想リストの値を増やし、増やす前の値を返す -/
def bump (k : Nat) : List (Nat × Nat) → Nat × List (Nat × Nat)
  | [] => (0, [(k, 1)])
  | (a, v) :: t =>
    if a == k then (v, (a, v + 1) :: t)
    else
      let (r, t') := bump k t
      (r, (a, v) :: t')

def countOf (k : Nat) : List (Nat × Nat) → Nat
  | [] => 0
  | (a, v) :: t => if a == k then v else countOf k t

structure Slots where
  srcPort : Nat
  dstPort : Nat
  ht1 : Nat   -- 始点側の水平溝のトラック
  ht2 : Nat   -- 終点側の水平溝のトラック
  vt : Nat    -- 垂直溝のトラック
  hg1 : Nat
  hg2 : Nat
  vg : Nat
  far : Bool
  deriving Repr

structure Counters where
  ports : List (Nat × Nat)
  hg : List (Nat × Nat)
  vg : List (Nat × Nat)

def assignOne (cols : Nat) (c : Counters) (rp : RelPlan) : Slots × Counters :=
  let (sp, ports1) := bump (sideKey cols rp.srcCell rp.srcSide) c.ports
  let (dp, ports2) := bump (sideKey cols rp.dstCell rp.dstSide) ports1
  let a := rp.srcCell
  let b := rp.dstCell
  match rp.srcSide with
  | .right =>
    let (vt, vg1) := bump (a.col + 1) c.vg
    (⟨sp, dp, 0, 0, vt, 0, 0, a.col + 1, false⟩, ⟨ports2, c.hg, vg1⟩)
  | _ =>
    if a.row == b.row then
      let (t, hg1) := bump (a.row + 1) c.hg
      (⟨sp, dp, t, t, 0, a.row + 1, a.row + 1, 0, false⟩, ⟨ports2, hg1, c.vg⟩)
    else
      let gs := if a.row < b.row then a.row + 1 else a.row
      let gd := if a.row < b.row then b.row else b.row + 1
      if gs == gd then
        let (t, hg1) := bump gs c.hg
        (⟨sp, dp, t, t, 0, gs, gd, 0, false⟩, ⟨ports2, hg1, c.vg⟩)
      else
        let (t1, hg1) := bump gs c.hg
        let (t2, hg2) := bump gd hg1
        let (vt, vg1) := bump b.col c.vg
        (⟨sp, dp, t1, t2, vt, gs, gd, b.col, true⟩, ⟨ports2, hg2, vg1⟩)

def assignAll (cols : Nat) (rps : List RelPlan) (c : Counters) : List Slots × Counters :=
  match rps with
  | [] => ([], c)
  | rp :: t =>
    let (s, c1) := assignOne cols c rp
    let (r, c2) := assignAll cols t c1
    (s :: r, c2)

structure Cols where
  key : Nat
  name : Nat
  ty : Nat
  note : Nat
  deriving Repr

def keyText (a : PAttr) : Bytes := sepBy b!"," (keyList a)
def absentType : Bytes := b!"（型の記載なし）"
def typeText (a : PAttr) : Bytes := a.ty.getD absentType

def attrCols (e : PEnt) : Cols :=
  ⟨maxL (e.attrs.map fun a => textW (keyText a)),
   maxL (e.attrs.map fun a => textW a.name),
   maxL (e.attrs.map fun a => textW (typeText a)),
   maxL (e.attrs.map fun a => match a.note with | some n => textW n | none => 0)⟩

def headerH : Nat := 34
def rowH : Nat := 22

def contentW (e : PEnt) : Nat :=
  let c := attrCols e
  max (textW e.name + 28)
    (if e.attrs.isEmpty then 0
     else 12 + c.key + 14 + c.name + 14 + c.ty + (if c.note == 0 then 0 else 14 + c.note) + 12)

def contentH (e : PEnt) : Nat :=
  if e.attrs.isEmpty then 44 else headerH + rowH * e.attrs.length + 8

structure Box where
  id : Bytes
  x : Nat
  y : Nat
  w : Nat
  h : Nat
  deriving DecidableEq, Repr

structure Scene where
  w : Nat
  h : Nat
  boxes : List (PEnt × Box)
  routes : List (PRel × List Pt × Pt)  -- 経路とラベル位置
  deriving Repr

def rangeL : Nat → List Nat
  | 0 => []
  | n + 1 => rangeL n ++ [n]

def sumTo (f : Nat → Nat) : Nat → Nat
  | 0 => 0
  | n + 1 => sumTo f n + f n

def hgH (c : Nat) : Nat := if c == 0 then 44 else 68 + 20 * (c - 1)
def vgW (c : Nat) : Nat := if c == 0 then 44 else 68 + 20 * (c - 1)

def margin : Nat := 20

structure Geo where
  order : List Bytes
  cols : Nat
  rows : Nat
  colW : Nat → Nat
  rowH' : Nat → Nat
  gapV : Nat → Nat
  gapH : Nat → Nat

def Geo.colX (g : Geo) (c : Nat) : Nat :=
  margin + sumTo (fun i => g.gapV i + g.colW i) c + g.gapV c
def Geo.rowY (g : Geo) (r : Nat) : Nat :=
  margin + sumTo (fun i => g.gapH i + g.rowH' i) r + g.gapH r
def Geo.gapVX (g : Geo) (c : Nat) : Nat :=
  margin + sumTo (fun i => g.gapV i + g.colW i) c
def Geo.gapHY (g : Geo) (r : Nat) : Nat :=
  margin + sumTo (fun i => g.gapH i + g.rowH' i) r

def portPt (b : Box) (s : Side) (i : Nat) : Pt :=
  match s with
  | .bottom => ⟨b.x + 24 + 28 * i, b.y + b.h⟩
  | .top => ⟨b.x + 38 + 28 * i, b.y⟩
  | .right => ⟨b.x + b.w, b.y + 14 + 28 * i⟩

def routeOf (g : Geo) (a b : Box) (rp : RelPlan) (s : Slots) : List Pt :=
  let p0 := portPt a rp.srcSide s.srcPort
  let p1 := portPt b rp.dstSide s.dstPort
  match rp.srcSide with
  | .right =>
    let x := g.gapVX s.vg + 34 + 20 * s.vt
    [p0, ⟨x, p0.y⟩, ⟨x, p1.y⟩, p1]
  | _ =>
    let y1 := g.gapHY s.hg1 + 34 + 20 * s.ht1
    if s.far then
      let y2 := g.gapHY s.hg2 + 34 + 20 * s.ht2
      let x := g.gapVX s.vg + 20 + 20 * s.vt
      [p0, ⟨p0.x, y1⟩, ⟨x, y1⟩, ⟨x, y2⟩, ⟨p1.x, y2⟩, p1]
    else
      [p0, ⟨p0.x, y1⟩, ⟨p1.x, y1⟩, p1]

def diff (a b : Nat) : Nat := (a - b) + (b - a)

/-- 最も長い水平区間 -/
def longestH : List Pt → Option (Pt × Pt)
  | a :: b :: t =>
    let rest := longestH (b :: t)
    if a.y == b.y then
      match rest with
      | some (c, d) => if diff c.x d.x > diff a.x b.x then some (c, d) else some (a, b)
      | none => some (a, b)
    else rest
  | _ => none

def segs : List Pt → List (Pt × Pt)
  | a :: b :: t => (a, b) :: segs (b :: t)
  | _ => []

def crossesV (x1 x2 y : Nat) (s : Pt × Pt) : Bool :=
  s.1.x == s.2.x && x1 ≤ s.1.x && s.1.x ≤ x2 && min s.1.y s.2.y ≤ y && y - 14 ≤ max s.1.y s.2.y

/-- ラベル位置: 水平区間上の候補から、他の経路の垂直線と重ならない最初の点 -/
def labelAt (allSegs : List (Pt × Pt)) (route : List Pt) (lab : Bytes) : Pt :=
  match longestH route with
  | none => ⟨0, 0⟩
  | some (a, b) =>
    -- 水平区間から始まる経路は自己関係で、端点記号の分だけ離す
    let startsFlat := match route with | p :: q :: _ => p.y == q.y | _ => false
    let lo := min a.x b.x + (if startsFlat then 30 else if diff a.x b.x < 8 then 0 else 8)
    let hi := max a.x b.x
    let y := a.y - 5
    let w := textW lab
    let cand := ((rangeL 6).map fun i => lo + i * 20).filter (· ≤ hi)
    let ok (x : Nat) : Bool := !allSegs.any (crossesV x (x + w) a.y)
    match cand.filter ok with
    | x :: _ => ⟨x, y⟩
    | [] => ⟨lo, y⟩

def zip3 {α β γ} : List α → List β → List γ → List (α × β × γ)
  | a :: t, b :: u, c :: v => (a, b, c) :: zip3 t u v
  | _, _, _ => []

def layout (p : PModel) : Scene :=
  let order := bfsOrder p
  let n := order.length
  let cols := max 1 (isqrtCeil n)
  let rows := if n == 0 then 0 else (n + cols - 1) / cols
  let plans := p.rels.map (planRel order cols)
  let (slots, cnt) := assignAll cols plans ⟨[], [], []⟩
  let ents := order.flatMap fun i => p.ents.filter (·.id == i)
  let idx := (rangeL n)
  let bw (i : Nat) (e : PEnt) : Nat :=
    let c : Cell := ⟨i % cols, i / cols⟩
    max (contentW e)
      (52 + 28 * max (countOf (sideKey cols c .bottom) cnt.ports)
                     (countOf (sideKey cols c .top) cnt.ports))
  let bh (i : Nat) (e : PEnt) : Nat :=
    let c : Cell := ⟨i % cols, i / cols⟩
    max (contentH e) (28 * countOf (sideKey cols c .right) cnt.ports + 16)
  let sized := (idx.zip ents).map fun (i, e) => (i, e, bw i e, bh i e)
  let colW (c : Nat) := maxL (sized.map fun (i, _, w, _) => if i % cols == c then w else 0)
  let rowW (r : Nat) := maxL (sized.map fun (i, _, _, h) => if i / cols == r then h else 0)
  let colTab := (rangeL cols).map colW
  let rowTab := (rangeL rows).map rowW
  let gapVTab := (rangeL (cols + 1)).map fun c => vgW (countOf c cnt.vg)
  let gapHTab := (rangeL (rows + 1)).map fun c => hgH (countOf c cnt.hg)
  let g : Geo := ⟨order, cols, rows, (colTab.getD · 0), (rowTab.getD · 0),
                  (gapVTab.getD · 0), (gapHTab.getD · 0)⟩
  let boxes := sized.map fun (i, e, w, h) =>
    (e, (⟨e.id, g.colX (i % cols), g.rowY (i / cols), w, h⟩ : Box))
  let box (x : Bytes) : Box :=
    match boxes.filter (fun b => b.2.id == x) with
    | b :: _ => b.2
    | [] => ⟨x, 0, 0, 0, 0⟩
  let plain := (zip3 p.rels plans slots).map fun (r, rp, s) => routeOf g (box r.src) (box r.dst) rp s
  let allSegs := plain.flatMap segs
  let routes := (p.rels.zip plain).map fun (r, rt) =>
    (r, rt, labelAt allSegs rt (r.label.getD Bytes.nil))
  let labelEnd := maxL (routes.map fun (r, _, l) => l.x + textW (r.label.getD Bytes.nil))
  let w := max (g.gapVX cols + (gapVTab.getD cols 0) + margin) (labelEnd + margin)
  let h := g.gapHY rows + (gapHTab.getD rows 0) + margin
  ⟨w, h, boxes, routes⟩

/-! ### 幾何検査 -/

def boxesDisjoint (a b : Box) : Bool :=
  a.x + a.w < b.x || b.x + b.w < a.x || a.y + a.h < b.y || b.y + b.h < a.y

def allPairs {α} (f : α → α → Bool) : List α → Bool
  | [] => true
  | a :: t => t.all (f a) && allPairs f t

def orthogonal (s : Pt × Pt) : Bool := (s.1.x == s.2.x) != (s.1.y == s.2.y)

/-- 線分が箱の内部（境界を除く）を通らない -/
def avoids (b : Box) (s : Pt × Pt) : Bool :=
  let x1 := min s.1.x s.2.x
  let x2 := max s.1.x s.2.x
  let y1 := min s.1.y s.2.y
  let y2 := max s.1.y s.2.y
  x2 ≤ b.x || b.x + b.w ≤ x1 || y2 ≤ b.y || b.y + b.h ≤ y1

def onBoundary (b : Box) (p : Pt) : Bool :=
  let inX := b.x ≤ p.x && p.x ≤ b.x + b.w
  let inY := b.y ≤ p.y && p.y ≤ b.y + b.h
  (inX && (p.y == b.y || p.y == b.y + b.h)) || (inY && (p.x == b.x || p.x == b.x + b.w))

def noCollinearOverlap (s t : Pt × Pt) : Bool :=
  if s.1.x == s.2.x && t.1.x == t.2.x && s.1.x == t.1.x then
    max s.1.y s.2.y ≤ min t.1.y t.2.y || max t.1.y t.2.y ≤ min s.1.y s.2.y
  else if s.1.y == s.2.y && t.1.y == t.2.y && s.1.y == t.1.y then
    max s.1.x s.2.x ≤ min t.1.x t.2.x || max t.1.x t.2.x ≤ min s.1.x s.2.x
  else true

def segLen (s : Pt × Pt) : Nat := diff s.1.x s.2.x + diff s.1.y s.2.y

def lastPt : List Pt → Pt
  | [] => ⟨0, 0⟩
  | [a] => a
  | _ :: t => lastPt t

def endSegs (r : List Pt) : Option ((Pt × Pt) × (Pt × Pt)) :=
  match segs r, segs r.reverse with
  | a :: _, b :: _ => some (a, b)
  | _, _ => none

def routeOk (bs : List Box) (rt : PRel × List Pt × Pt) : Bool :=
  let (r, pts, _) := rt
  let ss := segs pts
  let box (x : Bytes) := bs.filter (·.id == x)
  match box r.src, box r.dst, pts.head?, endSegs pts with
  | a :: _, b :: _, some p0, some (s0, s1) =>
    onBoundary a p0 && onBoundary b (lastPt pts)
      && ss.all orthogonal
      && 26 ≤ segLen s0 && 26 ≤ segLen s1
      && bs.all (fun x => ss.all (avoids x))
  | _, _, _, _ => false

def textFits (e : PEnt) (b : Box) : Bool :=
  contentW e ≤ b.w && contentH e ≤ b.h

/-- 自動配置の幾何条件。文字幅は textW の推定値で、実描画の確認はカーネル外 -/
def layoutOk (sc : Scene) : Bool :=
  let bs := sc.boxes.map (·.2)
  let allSegs := sc.routes.flatMap fun (_, pts, _) => segs pts
  allPairs boxesDisjoint bs
    && bs.all (fun b => b.x + b.w ≤ sc.w && b.y + b.h ≤ sc.h)
    && allSegs.all (fun s => max s.1.x s.2.x ≤ sc.w && max s.1.y s.2.y ≤ sc.h)
    && sc.boxes.all (fun (e, b) => textFits e b)
    && sc.routes.all (routeOk bs)
    && allPairs noCollinearOverlap allSegs

/-- 他の線と重なるラベルの数（見やすさの指標。合否には使わない） -/
def labelCrossings (sc : Scene) : Nat :=
  let allSegs := sc.routes.flatMap fun (_, pts, _) => segs pts
  (sc.routes.filter fun (r, _, l) =>
    match r.label with
    | none => false
    | some lab => allSegs.any (crossesV l.x (l.x + textW lab) (l.y + 5))).length

/-! ## SVG 生成 -/

def escXml (s : Bytes) : Bytes :=
  ofList (s.toList.flatMap fun c =>
    if c == 38 then (b!"&amp;").toList
    else if c == 60 then (b!"&lt;").toList
    else if c == 62 then (b!"&gt;").toList
    else if c == 34 then (b!"&quot;").toList
    else [c])

def svgHeader (w h : Nat) : Bytes :=
  b!"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"" ++ natB w ++ b!"\" height=\"" ++ natB h
    ++ b!"\" viewBox=\"0 0 " ++ natB w ++ b!" " ++ natB h
    ++ b!"\" font-size=\"13\" font-family=\"Menlo,Consolas,'Hiragino Sans','Noto Sans CJK JP','Yu Gothic',sans-serif\">"

def strokeA : Bytes := b!" fill=\"none\" stroke=\"#1f2933\" stroke-width=\"1.5\"/>"

def svgBox (b : Box) : Bytes :=
  b!"<rect id=\"" ++ b.id ++ b!"\" x=\"" ++ natB b.x ++ b!"\" y=\"" ++ natB b.y ++ b!"\" width=\""
    ++ natB b.w ++ b!"\" height=\"" ++ natB b.h ++ b!"\" fill=\"#ffffff\" stroke=\"#1f2933\" stroke-width=\"1.5\"/>"

def svgName (e : PEnt) (b : Box) : Bytes :=
  b!"<text x=\"" ++ natB (b.x + 12) ++ b!"\" y=\"" ++ natB (b.y + (if e.attrs.isEmpty then 26 else 22))
    ++ b!"\" font-weight=\"700\">" ++ escXml e.name ++ b!"</text>"

def svgRule (b : Box) : Bytes :=
  b!"<path d=\"M " ++ natB b.x ++ b!" " ++ natB (b.y + headerH - 2) ++ b!" L " ++ natB (b.x + b.w) ++ b!" "
    ++ natB (b.y + headerH - 2) ++ b!"\" fill=\"none\" stroke=\"#9aa5b1\" stroke-width=\"1\"/>"

def svgAttr (b : Box) (c : Cols) (i : Nat) (a : PAttr) : Bytes :=
  let x0 := b.x + 12
  let x1 := x0 + c.key + 14
  let x2 := x1 + c.name + 14
  let x3 := x2 + c.ty + 14
  b!"<text y=\"" ++ natB (b.y + headerH + 15 + rowH * i) ++ b!"\"><tspan x=\"" ++ natB x0
    ++ b!"\" font-weight=\"700\">" ++ keyText a ++ b!"</tspan><tspan x=\"" ++ natB x1 ++ b!"\">"
    ++ escXml a.name ++ b!"</tspan><tspan x=\"" ++ natB x2 ++ b!"\" fill=\""
    ++ (if a.ty.isNone then b!"#7b8794" else b!"#1f2933") ++ b!"\">"
    ++ escXml (typeText a) ++ b!"</tspan>"
    ++ (match a.note with
        | some n => b!"<tspan x=\"" ++ natB x3 ++ b!"\" fill=\"#52606d\">" ++ escXml n ++ b!"</tspan>"
        | none => Bytes.nil)
    ++ b!"</text>"

def svgAttrs (b : Box) (c : Cols) : Nat → List PAttr → List Bytes
  | _, [] => []
  | i, a :: t => svgAttr b c i a :: svgAttrs b c (i + 1) t

def svgEnt (e : PEnt) (b : Box) : List Bytes :=
  [svgBox b, svgName e b]
    ++ (if e.attrs.isEmpty then [] else svgRule b :: svgAttrs b (attrCols e) 0 e.attrs)

def pathD : List Pt → Bytes
  | [] => Bytes.nil
  | p :: t => b!"M " ++ natB p.x ++ b!" " ++ natB p.y
      ++ concat (t.map fun q => b!" L " ++ natB q.x ++ b!" " ++ natB q.y)

inductive Dir | up | down | right deriving DecidableEq, Repr

/-- 箱から線の外向き。endpoint から次の点への向き -/
def dirOf (p q : Pt) : Option Dir :=
  if p.x == q.x then
    if p.y < q.y then some .down else if q.y < p.y then some .up else none
  else if p.y == q.y && p.x < q.x then some .right
  else if p.y == q.y && q.x < p.x then some .right
  else none

/-- 外向き d に距離 dist 進み、垂直方向へ off 進んだ点。off は pos/neg で符号を分ける -/
def along (p : Pt) (right : Bool) (d : Dir) (dist off : Nat) (pos : Bool) : Pt :=
  let main : Pt :=
    match d with
    | .up => ⟨p.x, p.y - dist⟩
    | .down => ⟨p.x, p.y + dist⟩
    | .right => if right then ⟨p.x + dist, p.y⟩ else ⟨p.x - dist, p.y⟩
  match d with
  | .right => ⟨main.x, if pos then main.y + off else main.y - off⟩
  | _ => ⟨if pos then main.x + off else main.x - off, main.y⟩

def symStroke : Bytes := b!" stroke=\"#1f2933\" stroke-width=\"1.5\"/>"

def svgBar (p : Pt) (rt : Bool) (d : Dir) (dist : Nat) : Bytes :=
  let a := along p rt d dist 7 false
  let c := along p rt d dist 7 true
  b!"<line x1=\"" ++ natB a.x ++ b!"\" y1=\"" ++ natB a.y ++ b!"\" x2=\"" ++ natB c.x ++ b!"\" y2=\""
    ++ natB c.y ++ b!"\"" ++ symStroke

def svgCircle (p : Pt) (rt : Bool) (d : Dir) (dist : Nat) : Bytes :=
  let c := along p rt d dist 0 true
  b!"<circle cx=\"" ++ natB c.x ++ b!"\" cy=\"" ++ natB c.y ++ b!"\" r=\"5\" fill=\"#ffffff\"" ++ symStroke

def svgCrow (p : Pt) (rt : Bool) (d : Dir) : Bytes :=
  let a := along p rt d 0 8 false
  let m := along p rt d 12 0 true
  let c := along p rt d 0 8 true
  b!"<path d=\"M " ++ natB a.x ++ b!" " ++ natB a.y ++ b!" L " ++ natB m.x ++ b!" " ++ natB m.y
    ++ b!" L " ++ natB c.x ++ b!" " ++ natB c.y ++ b!"\" fill=\"none\"" ++ symStroke

/-- 内側・外側の2記号で多重度を描く -/
def svgMult (p : Pt) (rt : Bool) (d : Dir) : Mult → List Bytes
  | .one => [svgBar p rt d 8, svgBar p rt d 15]
  | .zeroOne => [svgBar p rt d 8, svgCircle p rt d 20]
  | .oneMany => [svgCrow p rt d, svgBar p rt d 19]
  | .zeroMany => [svgCrow p rt d, svgCircle p rt d 20]
  | .unknown => []

def endDir (a b : Pt) : Dir × Bool :=
  match dirOf a b with
  | some .right => (.right, a.x < b.x)
  | some d => (d, true)
  | none => (.down, true)

def svgRel (i : Nat) (rt : PRel × List Pt × Pt) : List Bytes :=
  let (r, pts, lab) := rt
  match endSegs pts with
  | none => []
  | some (s0, s1) =>
    let (d0, r0) := endDir s0.1 s0.2
    let (d1, r1) := endDir s1.1 s1.2
    [b!"<path id=\"R" ++ natB (i + 1) ++ b!"\" d=\"" ++ pathD pts ++ b!"\" fill=\"none\" stroke=\"#1f2933\" stroke-width=\"1.5\""
      ++ (match r.line with | .solid => Bytes.nil | .dashed => b!" stroke-dasharray=\"6 4\"") ++ b!"/>"]
    ++ svgMult s0.1 r0 d0 r.sm ++ svgMult s1.1 r1 d1 r.dm
    ++ (match r.label with
        | some l => [b!"<text x=\"" ++ natB lab.x ++ b!"\" y=\"" ++ natB lab.y
            ++ b!"\" fill=\"#1f2933\">" ++ escXml l ++ b!"</text>"]
        | none => [])

def svgRels : Nat → List (PRel × List Pt × Pt) → List Bytes
  | _, [] => []
  | i, rt :: t => svgRel i rt ++ svgRels (i + 1) t

def renderSvgLines (sc : Scene) : List Bytes :=
  [svgHeader sc.w sc.h,
   b!"<rect x=\"0\" y=\"0\" width=\"" ++ natB sc.w ++ b!"\" height=\"" ++ natB sc.h ++ b!"\" fill=\"#ffffff\"/>"]
  ++ sc.boxes.flatMap (fun (e, b) => svgEnt e b)
  ++ svgRels 0 sc.routes
  ++ [b!"</svg>"]

def renderSvg (sc : Scene) : Bytes := joinLines (renderSvgLines sc)

/-! ## SVG 限定読取（生成関数を呼ばない） -/

def symStrokeK : List Nat := k!" stroke=\"#1f2933\" stroke-width=\"1.5\"/>"


def parseNat (l : List Nat) : Option (Nat × List Nat) :=
  let (d, r) := spanWhile isDigit l
  if d.isEmpty then none
  else some (d.foldl (fun a c => a * 10 + (c - 48)) 0, r)

/-- 「lit 数値 "」の読み取り -/
def numAttr (key : List Nat) (l : List Nat) : Option (Nat × List Nat) :=
  match lit key l with
  | none => none
  | some r =>
    match parseNat r with
    | none => none
    | some (v, r1) =>
      match lit k!"\"" r1 with
      | none => none
      | some r2 => some (v, r2)

def unescXml : Nat → List Nat → Option (List Nat)
  | 0, _ => none
  | _, [] => some []
  | f + 1, 38 :: t =>
    match lit k!"amp;" t with
    | some r => (38 :: ·) <$> unescXml f r
    | none => match lit k!"lt;" t with
      | some r => (60 :: ·) <$> unescXml f r
      | none => match lit k!"gt;" t with
        | some r => (62 :: ·) <$> unescXml f r
        | none => match lit k!"quot;" t with
          | some r => (34 :: ·) <$> unescXml f r
          | none => none
  | f + 1, c :: t => if c == 60 then none else (c :: ·) <$> unescXml f t

def textUntilClose (l : List Nat) (close : List Nat) : Option (Bytes × List Nat) :=
  match untilByte 60 l with
  | none => none
  | some (raw, r) =>
    match lit close (60 :: r) with
    | none => none
    | some r1 =>
      match unescXml (raw.length + 2) raw with
      | some u => some (ofList u, r1)
      | none => none

structure RBox where
  id : Bytes
  b : Box
  deriving Repr

def parseRect (line : Bytes) : Option Box :=
  let l := line.toList
  match lit k!"<rect id=\"" l with
  | none => none
  | some r =>
    let (id, r1) := spanWhile isIdChar r
    if id.isEmpty then none else
    match numAttr k!"\" x=\"" r1 with
    | none => none
    | some (x, r2) =>
      match numAttr k!" y=\"" r2 with
      | none => none
      | some (y, r3) =>
        match numAttr k!" width=\"" r3 with
        | none => none
        | some (w, r4) =>
          match numAttr k!" height=\"" r4 with
          | none => none
          | some (h, r5) =>
            match lit k!" fill=\"#ffffff\" stroke=\"#1f2933\" stroke-width=\"1.5\"/>" r5 with
            | some [] => some ⟨ofList id, x, y, w, h⟩
            | _ => none

/-- 表示名の位置が箱の内側にあることも確かめる -/
def parseName (b : Box) (line : Bytes) : Option Bytes :=
  let l := line.toList
  match numAttr k!"<text x=\"" l with
  | none => none
  | some (x, r) =>
    match numAttr k!" y=\"" r with
    | none => none
    | some (y, r1) =>
      if !(b.x < x && x < b.x + b.w && b.y < y && y < b.y + b.h) then none else
      match lit k!" font-weight=\"700\">" r1 with
      | none => none
      | some r2 =>
        match textUntilClose r2 k!"</text>" with
        | some (s, []) => some s
        | _ => none

def isRule (b : Box) (line : Bytes) : Bool :=
  let l := line.toList
  match lit k!"<path d=\"M " l with
  | none => false
  | some r =>
    match parseNat r with
    | none => false
    | some (x, r1) =>
      x == b.x && (lit k!" " r1).isSome && (spanWhile isDigit ((lit k!" " r1).getD [])).2.take 3 == [32, 76, 32]

def parseKeyText (l : List Nat) : Option (Bool × Bool × Bool) :=
  let step (k : List Nat) (r : List Nat) : Bool × List Nat :=
    match lit k r with
    | some r' => (true, match lit k!"," r' with | some r'' => r'' | none => r')
    | none => (false, r)
  let (pk, r1) := step k!"PK" l
  let (fk, r2) := step k!"FK" r1
  let (uk, r3) := step k!"UK" r2
  if r3.isEmpty then some (pk, fk, uk) else none

def tspanOpen (l : List Nat) (suffix : List Nat) : Option (Nat × List Nat) :=
  match numAttr k!"<tspan x=\"" l with
  | none => none
  | some (x, r) =>
    match lit suffix r with
    | none => none
    | some r1 => some (x, r1)

def parseAttrLine (b : Box) (line : Bytes) : Option PAttr :=
  let l := line.toList
  match numAttr k!"<text y=\"" l with
  | none => none
  | some (y, r) =>
    if !(b.y < y && y < b.y + b.h) then none else
    match lit k!">" r with
    | none => none
    | some r0 =>
      match tspanOpen r0 k!" font-weight=\"700\">" with
      | none => none
      | some (x0, r1) =>
        if !(b.x < x0 && x0 < b.x + b.w) then none else
        match untilByte 60 r1 with
        | none => none
        | some (ktext, r2raw) =>
          match lit k!"/tspan>" r2raw, parseKeyText ktext with
          | some r2, some (pk, fk, uk) =>
            match tspanOpen r2 k!">" with
            | none => none
            | some (_, r3) =>
              match textUntilClose r3 k!"</tspan>" with
              | none => none
              | some (nm, r4) =>
                match numAttr k!"<tspan x=\"" r4 with
                | none => none
                | some (_, r5) =>
                  let tyInfo : Option (Bool × List Nat) :=
                    match lit k!" fill=\"#7b8794\">" r5 with
                    | some r6 => some (true, r6)
                    | none => match lit k!" fill=\"#1f2933\">" r5 with
                      | some r6 => some (false, r6)
                      | none => none
                  match tyInfo with
                  | none => none
                  | some (absent, r6) =>
                    match textUntilClose r6 k!"</tspan>" with
                    | none => none
                    | some (tyT, r7) =>
                      if absent && tyT != absentType then none else
                      let ty := if absent then none else some tyT
                      match lit k!"</text>" r7 with
                      | some [] => some ⟨nm, ty, pk, fk, uk, none⟩
                      | _ =>
                        match tspanOpen r7 k!" fill=\"#52606d\">" with
                        | none => none
                        | some (_, r8) =>
                          match textUntilClose r8 k!"</tspan></text>" with
                          | some (nt, []) => some ⟨nm, ty, pk, fk, uk, some nt⟩
                          | _ => none
          | _, _ => none

def parseAttrLines (b : Box) : List Bytes → List PAttr × List Bytes
  | [] => ([], [])
  | l :: t =>
    match parseAttrLine b l with
    | some a =>
      let (r, rest) := parseAttrLines b t
      (a :: r, rest)
    | none => ([], l :: t)

def parsePts (l : List Nat) : Nat → Option (List Pt × List Nat)
  | 0 => none
  | f + 1 =>
    match parseNat l with
    | none => none
    | some (x, r) =>
      match lit k!" " r with
      | none => none
      | some r1 =>
        match parseNat r1 with
        | none => none
        | some (y, r2) =>
          match lit k!" L " r2 with
          | some r3 =>
            match parsePts r3 f with
            | some (ps, r4) => some (⟨x, y⟩ :: ps, r4)
            | none => none
          | none => some ([⟨x, y⟩], r2)

inductive Sym
  | bar (a c : Pt)
  | circle (c : Pt)
  | crow (a m c : Pt)
  deriving DecidableEq, Repr

def parseSym (line : Bytes) : Option Sym :=
  let l := line.toList
  match numAttr k!"<line x1=\"" l with
  | some (x1, r) =>
    match numAttr k!" y1=\"" r with
    | none => none
    | some (y1, r1) =>
      match numAttr k!" x2=\"" r1 with
      | none => none
      | some (x2, r2) =>
        match numAttr k!" y2=\"" r2 with
        | none => none
        | some (y2, r3) =>
          match lit symStrokeK r3 with
          | some [] => some (.bar ⟨x1, y1⟩ ⟨x2, y2⟩)
          | _ => none
  | none =>
    match numAttr k!"<circle cx=\"" l with
    | some (x, r) =>
      match numAttr k!" cy=\"" r with
      | none => none
      | some (y, r1) =>
        match lit k!" r=\"5\" fill=\"#ffffff\"" r1 with
        | none => none
        | some r2 =>
          match lit symStrokeK r2 with
          | some [] => some (.circle ⟨x, y⟩)
          | _ => none
    | none =>
      match lit k!"<path d=\"M " l with
      | none => none
      | some r =>
        match parsePts r 4 with
        | some ([a, m, c], r1) =>
          match lit k!"\" fill=\"none\"" r1 with
          | none => none
          | some r2 =>
            match lit symStrokeK r2 with
            | some [] => some (.crow a m c)
            | _ => none
        | _ => none

/-- 2記号の形と、端点からの距離・向きを実座標で確かめて多重度にする -/
def isBarAt (p : Pt) (rt : Bool) (d : Dir) (dist : Nat) : Sym → Bool
  | .bar a c => a == along p rt d dist 7 false && c == along p rt d dist 7 true
  | _ => false
def isCircleAt (p : Pt) (rt : Bool) (d : Dir) (dist : Nat) : Sym → Bool
  | .circle c => c == along p rt d dist 0 true
  | _ => false
def isCrowAt (p : Pt) (rt : Bool) (d : Dir) : Sym → Bool
  | .crow a m c => a == along p rt d 0 8 false && m == along p rt d 12 0 true && c == along p rt d 0 8 true
  | _ => false

def readMult (p : Pt) (rt : Bool) (d : Dir) (s1 s2 : Sym) : Option Mult :=
  if isBarAt p rt d 8 s1 && isBarAt p rt d 15 s2 then some .one
  else if isBarAt p rt d 8 s1 && isCircleAt p rt d 20 s2 then some .zeroOne
  else if isCrowAt p rt d s1 && isBarAt p rt d 19 s2 then some .oneMany
  else if isCrowAt p rt d s1 && isCircleAt p rt d 20 s2 then some .zeroMany
  else none

/-- 端点が境界上にある箱を座標から探す。線が箱の外へ向かうことも確かめる -/
def findBox (bs : List Box) (p q : Pt) : Option Bytes :=
  match bs.filter (fun b => onBoundary b p && avoids b (p, q)) with
  | [b] => some b.id
  | _ => none

def parseRelPath (l : List Nat) : Option (List Pt × Line) :=
  match lit k!"<path id=\"R" l with
  | none => none
  | some r =>
    let (_, r1) := spanWhile isDigit r
    match lit k!"\" d=\"M " r1 with
    | none => none
    | some r2 =>
      match parsePts r2 16 with
      | none => none
      | some (pts, r3) =>
        match lit k!"\" fill=\"none\" stroke=\"#1f2933\" stroke-width=\"1.5\"" r3 with
        | none => none
        | some r4 =>
          match lit k!"/>" r4 with
          | some [] => some (pts, .solid)
          | _ =>
            match lit k!" stroke-dasharray=\"6 4\"/>" r4 with
            | some [] => some (pts, .dashed)
            | _ => none

/-- ラベルが自分の経路の水平区間の近くにあることを確かめる -/
def nearRoute (pts : List Pt) (x y : Nat) : Bool :=
  (segs pts).any fun s =>
    s.1.y == s.2.y && y + 5 == s.1.y && min s.1.x s.2.x ≤ x && x ≤ max s.1.x s.2.x

def parseLabel (pts : List Pt) (line : Bytes) : Option Bytes :=
  let l := line.toList
  match numAttr k!"<text x=\"" l with
  | none => none
  | some (x, r) =>
    match numAttr k!" y=\"" r with
    | none => none
    | some (y, r1) =>
      if !nearRoute pts x y then none else
      match lit k!" fill=\"#1f2933\">" r1 with
      | none => none
      | some r2 =>
        match textUntilClose r2 k!"</text>" with
        | some (s, []) => some s
        | _ => none

/-- 関係の4記号はすべて関係の直後にある固定形式。fuel は残行数 -/
def parseRels (bs : List Box) : Nat → List Bytes → Option (List PRel × List Bytes)
  | 0, _ => none
  | _, [] => some ([], [])
  | f + 1, l :: t =>
    match parseRelPath l.toList with
    | none => some ([], l :: t)
    | some (pts, line) =>
      match endSegs pts, t with
      | some (s0, s1), a :: b :: c :: d :: t1 =>
        let (d0, r0) := endDir s0.1 s0.2
        let (d1, r1) := endDir s1.1 s1.2
        match parseSym a, parseSym b, parseSym c, parseSym d,
              findBox bs s0.1 s0.2, findBox bs s1.1 s1.2 with
        | some sa, some sb, some sc, some sd, some src, some dst =>
          match readMult s0.1 r0 d0 sa sb, readMult s1.1 r1 d1 sc sd with
          | some sm, some dm =>
            let label := match t1 with
              | x :: _ => parseLabel pts x
              | [] => none
            let rest := match label, t1 with
              | some _, _ :: u => u
              | _, _ => t1
            match parseRels bs f rest with
            | some (rs, r2) => some (⟨src, dst, sm, dm, line, label⟩ :: rs, r2)
            | none => none
          | _, _ => none
        | _, _, _, _, _, _ => none
      | _, _ => none

/-- エンティティ部: rect → 表示名 → (区切り線 → 属性行)* -/
def parseEnts : Nat → List Bytes → Option (List (PEnt × Box) × List Bytes)
  | 0, _ => none
  | _, [] => some ([], [])
  | f + 1, l :: t =>
    match parseRect l, t with
    | some b, nameL :: t1 =>
      match parseName b nameL with
      | none => none
      | some nm =>
        let (attrs, t2) :=
          match t1 with
          | r :: u => if isRule b r then parseAttrLines b u else ([], t1)
          | [] => ([], t1)
        match parseEnts f t2 with
        | some (es, rest) => some ((⟨b.id, nm, attrs⟩, b) :: es, rest)
        | none => none
    | _, _ => some ([], l :: t)

def sortByOrder (ids : List Bytes) (es : List PEnt) : List PEnt :=
  ids.flatMap fun i => es.filter (·.id == i)

/-- SVG は配置順に並ぶため、id は期待順 order で意味モデルの順序へ戻す -/
def decodeSvgSubset (saved : Bytes) (lines : List Bytes) (order : List Bytes) : Option PModel :=
  if joinLines lines != saved || !lines.all noNl then none else
  match lines with
  | _hdr :: bg :: t =>
    if (lit k!"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"" _hdr.toList).isNone then none else
    if (lit k!"<rect x=\"0\" y=\"0\" width=\"" bg.toList).isNone then none else
    match parseEnts (t.length + 1) t with
    | none => none
    | some (es, r1) =>
      match parseRels (es.map (·.2)) (r1.length + 1) r1 with
      | some (rs, [c]) =>
        if c != b!"</svg>" then none
        else some ⟨sortByOrder order (es.map (·.1)), rs⟩
      | _ => none
  | _ => none

/-! ## 観察記録との対応（P-01） -/

inductive SymObs
  | barBar | circleBar | circleCrow | barCrow | ratioOne | ratioMany | user
  deriving DecidableEq, Repr

structure Ob where
  id : Bytes
  sym : Option SymObs
  deriving DecidableEq, Repr

structure Link where
  item : Bytes
  ob : Bytes
  deriving DecidableEq, Repr

/-- 確定した記号と多重度の対応。観察そのものの正しさは証明しない -/
def symAllows (s : SymObs) (m : Mult) : Bool :=
  match s, m with
  | .barBar, .one | .circleBar, .zeroOne | .circleCrow, .zeroMany | .barCrow, .oneMany => true
  | .ratioOne, .one | .ratioOne, .zeroOne => true
  | .ratioMany, .zeroMany | .ratioMany, .oneMany => true
  | .user, _ => true
  | _, _ => false

def requiredItems (m : Model) : List Bytes :=
  (m.ents.flatMap fun e =>
    (e.id ++ b!".name") :: (e.attrs.flatMap fun a =>
      (a.id ++ b!".name") :: (if a.pk || a.fk || a.uk then [a.id ++ b!".keys"] else [])
        ++ (if a.ty.isSome then [a.id ++ b!".type"] else [])))
  ++ (m.rels.flatMap fun r =>
    [r.id ++ b!".src", r.id ++ b!".dst", r.id ++ b!".src_multiplicity",
     r.id ++ b!".dst_multiplicity", r.id ++ b!".line"]
    ++ (if r.label.isSome then [r.id ++ b!".label"] else []))

def linkOf (ls : List Link) (item : Bytes) : Option Bytes :=
  match ls.filter (·.item == item) with
  | l :: _ => some l.ob
  | [] => none

def obOf (os : List Ob) (id : Bytes) : Option Ob :=
  match os.filter (·.id == id) with
  | o :: _ => some o
  | [] => none

def symConsistent (os : List Ob) (ls : List Link) (item : Bytes) (m : Mult) : Bool :=
  m == .unknown ||
  match linkOf ls item with
  | none => false
  | some oid =>
    match obOf os oid with
    | some ⟨_, some s⟩ => symAllows s m
    | _ => false

/-- 全項目に存在する観察への対応があり、確定した端点記号が多重度と一致する -/
def observationConsistent (os : List Ob) (ls : List Link) (m : Model) : Bool :=
  distinct (os.map (·.id))
    && (requiredItems m).all (fun it =>
        match linkOf ls it with
        | some oid => (obOf os oid).isSome
        | none => false)
    && m.rels.all fun r =>
        symConsistent os ls (r.id ++ b!".src_multiplicity") r.sm
          && symConsistent os ls (r.id ++ b!".dst_multiplicity") r.dm

/-! ## 実行時の書き出し -/

/-- 256 KiB でも二乗時間にならないよう半分ずつ分割して書き出す -/
def toBA : Nat → Nat → Nat → ByteArray → ByteArray
  | 0, _, _, acc => acc
  | f + 1, n, v, acc =>
    if n == 0 then acc
    else if n == 1 then acc.push (UInt8.ofNat v)
    else
      let lo := n / 2
      let p := 256 ^ lo
      toBA f lo (v % p) (toBA f (n - lo) (v / p) acc)

def Bytes.toByteArray (s : Bytes) : ByteArray := toBA 40 s.n s.v ByteArray.empty

def writeB (path : String) (s : Bytes) : IO Unit := IO.FS.writeBinFile path s.toByteArray

end Er
