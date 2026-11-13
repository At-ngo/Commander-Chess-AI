# CCHEF — Thiết kế và tối ưu hàm đánh giá Heuristic cho AI Cờ Tư Lệnh

> **Tên đề xuất:** Commander Chess Heuristic Evaluation Function (CCHEF)  
> **Mục đích:** Đặc tả đặc trưng, công thức đánh giá, lộ trình thực nghiệm H1–H7 và quy trình **Grid Search** để tìm trọng số phù hợp.  
> **Trạng thái:** Thiết kế nghiên cứu, **không phải** công thức tối ưu đã được kiểm chứng.  
> **Đơn vị quyết định:** Một **lượt hợp lệ** (`AtomicAction` hoặc `CompoundAction`), không phải mỗi chuyển động thành phần.

## 1. Mục tiêu và các ý tưởng nền tảng

AI cần biết (1) tích lũy và bảo toàn điểm quân, (2) bảo vệ Tư lệnh trước thế chiếu thực sự nguy hiểm, (3) tìm đường chiếu **an toàn**, (4) triển khai và kiểm soát giao điểm/địa hình, (5) khai thác cơ động và quân Anh hùng, (6) sử dụng **Hành quân thần tốc** để phối hợp ăn quân–chiếu–triển khai, (7) đánh giá quân **cõng nhau** như một tổ hợp có nguy cơ mất nhiều quân, và (8) điều chỉnh chiến thuật theo giai đoạn ván đấu.

| Mã | Ý tưởng | Cách tích hợp |
|---|---|---|
| M | Điểm quân chính thức | Material |
| HERO | Quân Anh hùng được +10 điểm và tăng tầm di chuyển | +10 trong Material; tầm mới qua Game Engine |
| K | An toàn Tư lệnh, cả các thế chiếu của đối phương | King Safety / chi phí phòng thủ |
| Q/SPC | Tạo thế chiếu an toàn, không dễ bị ăn | Safe Check Potential |
| P | Bày binh bố trận, chiếm/khống chế vị trí | Position / Terrain Control |
| C | Nước hợp lệ hữu ích, di chuyển an toàn | Mobility |
| D | Triển khai lực lượng nhanh, vận tải hợp lý | Deployment |
| T | Trao đổi quân, đe dọa, bảo vệ tổ hợp | Tactical Risk |
| CO | Hành quân thần tốc, ăn nhiều quân, vừa ăn vừa chiếu | Đánh giá **toàn bộ** CompoundAction + tactical analyzer |
| TC/TR | Ăn hoặc mất quân cõng lồng nhau | Giá trị tập quân bị loại và rủi ro tổ hợp |
| G | Khai cuộc, trung cuộc, tàn cuộc | Trọng số phụ thuộc giai đoạn (H7) |

**Nguyên tắc không đếm trùng:** Điểm quân đã bị loại chỉ ghi vào Material của trạng thái sau hành động. Tactical chỉ đánh giá *rủi ro/cơ hội chưa hiện thực hóa* và lợi thế phối hợp chưa được các đặc trưng khác phản ánh. Nếu K và Q cùng phản ánh một mối chiếu, cần xác định ranh giới hoặc kiểm tra tương quan/ablation.

## 2. Ký hiệu, Engine và quy tắc bất biến

- `s`: trạng thái bàn cờ; `p`: phe được đánh giá; `opp(p)`: phe kia.
- `U_p(s)`: toàn bộ quân **còn sống**, kể cả quân đang được chở; `V(u,s)`: điểm quân.
- `A(s)`: các **lượt** hợp lệ do Game Engine sinh từ `s`; mỗi phần tử có thể là `AtomicAction` hay `CompoundAction`.
- `T(s,a)`: bản sao trạng thái sau khi áp dụng **toàn bộ** hành động `a` (gồm phản ứng theo luật, thiệt hại đồng thời hoặc trì hoãn).
- `x̂`: giá trị đặc trưng chuẩn hóa; `w`: trọng số không âm.
- Bàn cờ 11 cột × 12 hàng; di chuyển trên **giao điểm**; địa hình LAND, SEA, RIVER_BANK, COAST và các loại cạnh liên quan.

Engine quyết định tính hợp lệ, cấm lộ mặt Tư lệnh, chiếu/chiếu hết, địa hình, Máy bay–Phòng không, bắn phá Hải quân, vận tải và phong Anh hùng. **Evaluator không tự sửa luật.** Với `CompoundAction`, không cho đối thủ xen lượt giữa các hành động con nếu luật coi đó là một lượt. Phải đếm quân bị loại duy nhất một lần.

### 2.1. Trạng thái kết thúc có ưu tiên tuyệt đối

\[
E(s,p)=\begin{cases}
+W,&\text{nếu }p\text{ thắng}\\
-W,&\text{nếu }p\text{ thua}\\
0,&\text{nếu hòa}\\
E_{\mathrm{static}}(s,p),&\text{nếu chưa kết thúc.}
\end{cases}
\]

`W` phải lớn hơn mọi trị tuyệt đối của `E_static`. Khi cần phân biệt thắng nhanh/chậm có thể dùng điểm mate-distance, nhưng không để điểm phụ lấn át kết quả thắng/thua. Xử lý hòa theo luật kết thúc Engine; giới hạn rollout kỹ thuật **không mặc nhiên** là hòa.

## 3. F1 — Material: giá trị quân và Anh hùng

| Quân | Điểm cơ bản |
|---|---:|
| Bộ binh | 10 |
| Cao xạ / Phòng không | 10 |
| Dân quân | 10 |
| Công binh | 10 |
| Xe tăng | 20 |
| Tên lửa | 20 |
| Pháo binh | 30 |
| Không quân / Máy bay | 40 |
| Hải quân | 80 |

**Tư lệnh** được xử lý bằng điều kiện thắng/thua, không quy đổi tùy tiện thành điểm. **Sở chỉ huy**: chờ xác nhận điểm quy định, không tự điền số. Điểm thưởng Anh hùng là 10, song điều kiện phong Anh hùng và khả năng di chuyển phải đọc từ Game Engine (không tự giả định được phong chỉ vì đang chiếu).

\[
V(u,s)=V_{base}(u)+10\,\mathbf{1}_{hero}(u,s)
\]
\[
M(s,p)=\sum_{u\in U_p(s)}V(u,s)-\sum_{v\in U_{opp(p)}(s)}V(v,s)
\]

Không bỏ sót quân được chở, vì chúng vẫn còn sống. Nếu quân cõng bị phá hủy, Engine loại tất cả quân phụ thuộc theo luật; chênh lệch Material sau lượt tự phản ánh tổn thất.

## 4. F2 — King Safety: chống các thế chiếu của đối phương

Phải phân biệt **có thể chiếu** với **chiếu có nguy hiểm thực sự**. Nếu quân đối phương chiếu nhưng ta có thể ăn quân chiếu **hợp lệ, an toàn**, không chịu tổn thất đáng kể thì thế chiếu có mức phạt rất thấp hoặc bằng 0. Ngoài ăn quân chiếu còn phải xét né/chặn/đỡ chiếu và các hậu quả sau đó.

Đặt `CheckOpp(s,p)` là tập phương án chiếu hợp lệ của `opp(p)` (tức thời hoặc ứng viên một lượt trong một bản trạng thái giả định phù hợp luật). Với `b` là một thế chiếu, `s_b=T(s,b)` và `Def(s_b,p)` là các lượt giải chiếu hợp lệ:

\[
D(b,p)=\min_{r\in Def(s_b,p)}Cost_{def}(T(s_b,r),p)
\]
\[
Risk(s,p)=\max_{b\in CheckOpp(s,p)}D(b,p),\qquad \max\varnothing=0
\]

`Cost_def` là **chi phí phòng thủ không âm** được chuẩn hóa, gồm vật chất cần hy sinh, hậu quả chiếu tiếp và mất thế trận. Nếu `Def` rỗng, kiểm tra Engine đã xác định thắng/thua hay chưa trước khi gán nguy cơ cực đại. Mức độ nguy hiểm của một đòn chiếu không được xác định chỉ từ số quân đang tấn công.

Đặc trưng hai chiều:

\[
K(s,p)=Risk(s,opp(p))-Risk(s,p)
\]

**Lưu ý tính toán:** Công thức `min`/`max` phía trên là *tactical lookahead*, không phải đặc trưng tĩnh rẻ tiền. Khi benchmark H1–H7, ghi rõ giới hạn kiểm tra (ví dụ: một lượt chiếu + một lượt giải chiếu) và thời gian xử lý; không nhầm với Minimax tìm kiếm cây đầy đủ.

## 5. F3 — Safe Check Potential (Q/SPC)

Ưu tiên các phương án tạo thế chiếu mà quân chiếu **không bị ăn an toàn ngay**, có khả năng buộc đối phương phòng thủ bất lợi, và khoảng cách triển khai không quá dài.

Với phương án chiếu ứng viên `a`:

\[
q(a)=\frac{Benefit(a)\cdot Safety(a)\cdot Force(a)}{1+Distance(a)}
\]

- `Benefit`: lợi ích tiềm năng của thế chiếu, không tính lại vật chất đã ăn.
- `Safety∈[0,1]`: quân chiếu có thể tồn tại/không bị ăn an toàn sau phản ứng hợp lệ.
- `Force∈[0,1]`: mức độ buộc đối phương sử dụng phản ứng có chi phí, không mặc định mọi thế chiếu đều hiệu quả.
- `Distance`: số **lượt** ước lượng để đạt thế chiếu, không đơn thuần khoảng cách hình học.

\[
Q(s,p)=\max_{a\in CheckPlan_p(s)}q(a)-\max_{b\in CheckPlan_{opp(p)}(s)}q(b)
\]

Với H4 cơ bản nên chỉ xét đường chiếu ngay hoặc sau **một lượt**. Tính chính xác đường chiếu sau 2–3 lượt có phản ứng đối phương thuộc phần *lookahead* của Minimax/Alpha-Beta. Tránh dùng cùng một phạt điểm cho một thế chiếu ở cả K và Q; có thể để K là chi phí phòng thủ thực tế, Q là khả năng chuẩn bị tấn công.

## 6. F4 — Position / Terrain Control

Khác cờ vua, vị trí tốt phụ thuộc giao điểm, loại quân và địa hình. Đặt `W(x,y)` là tầm quan trọng chiến lược của giao điểm `(x,y)` và `Control(s,p,x,y)` là mức kiểm soát hợp lệ của phe `p`:

\[
P(s,p)=\sum_{(x,y)}W(x,y)[Control(s,p,x,y)-Control(s,opp(p),x,y)]
\]

- Hải quân: tuyến nước/bờ và vùng bắn phá. **Bắn tới đất không có nghĩa được đứng trên đất.**
- Phòng không: bảo vệ vùng trọng yếu và chống Máy bay.
- Xe tăng, Pháo binh, Tên lửa: tuyến tấn công, hỗ trợ và khống chế.
- Máy bay: khả năng áp sát mục tiêu **trừ rủi ro** trong vành đai Phòng không.
- Không mặc định mọi ô trung tâm đều có điểm cao như cờ vua; cần thử nghiệm bảng vị trí theo địa hình.

## 7. F5 — Mobility: hành động hữu ích và an toàn

\[
C(s,p)=\sum_{u\in U_p(s)}m(u,s)-\sum_{v\in U_{opp(p)}(s)}m(v,s)
\]
\[
m(u,s)=\sum_{a\in A_u(s)}SafeMove(a)\cdot UsefulMove(a)
\]

Không chỉ đếm nước đi hợp lệ; một nước dẫn đến mất tổ hợp quân lớn có thể kém hữu ích. Cần API đánh giá khả năng của hai phe trên cùng trạng thái hợp lý, không chỉ gọi `legal_actions` của phe đến lượt rồi giả định có sẵn danh sách đối phương. **CompoundAction** có thể tạo bùng nổ số lượt; có thể dùng phép đo xấp xỉ nhất quán, có ghi rõ giới hạn.

## 8. F6 — Deployment: triển khai đội hình và hành quân nhanh

\[
D(s,p)=\sum_{u\in U_p(s)}Progress(u,s)-\sum_{v\in U_{opp(p)}(s)}Progress(v,s)
\]

`Progress` cần phản ánh mức tiếp cận vị trí có nhiệm vụ chiến thuật thực tế, khả năng bảo vệ/hỗ trợ và hiệu quả vận chuyển; **không phải** khoảng cách đi xa khỏi vị trí xuất phát. Một Phòng không đứng bảo vệ tuyến nhà có thể có điểm tốt. Khai cuộc có thể ưu tiên triển khai, nhưng một đòn thắng ngay vẫn vượt lên mọi điểm bố trận.

## 9. F7 — Tactical: ăn quân, tổ hợp cõng và rủi ro

### 9.1. Giá trị tổ hợp cõng lồng nhau

Gọi `Desc(u,s)` là mọi quân chở trực tiếp/gián tiếp bên trong `u` (không trùng ID):

\[
V_{stack}(u,s)=\sum_{v\in \{u\}\cup Desc(u,s)}V(v,s)
\]

Ví dụ: Xe tăng (20) chở Dân quân (10) ⇒ **30 điểm**. Máy bay (40) chở Xe tăng (20) đang chở Dân quân (10) ⇒ **70 điểm**, nếu tổ hợp này hợp lệ theo quy tắc vận tải.

### 9.2. Kết quả tiêu diệt thực tế

\[
Gain(s,a,p)=\sum_{u\in Removed_{opp(p)}(s,a)}V(u,s)
\]
\[
Loss(s,a,p)=\sum_{u\in Removed_p(s,a)}V(u,s)
\]
\[
TC(s,a,p)=Gain(s,a,p)-Loss(s,a,p)
\]

`Removed` lấy từ chuyển trạng thái Engine, bao gồm quân bị loại do phương tiện bị tiêu diệt và hậu quả Bom/Phòng không theo luật. **Không cộng `TC` lần nữa vào Material của trạng thái sau nước**; dùng nó cho giải thích quyết định, xếp hạng hành động, hoặc phân tích trước khi mô phỏng toàn bộ.

### 9.3. Nguy cơ mất tổ hợp

\[
TR(s,p)=\sum_{u\in RootStack_p}RiskLoss(u,s)\,V_{stack}(u,s)
\]

`RiskLoss` ban đầu có thể là hệ số ước lượng 0 / 0,5 / 1; chưa phải xác suất được hiệu chỉnh. Để tránh phạt trùng, chỉ tính các tổ hợp gốc và những quân không có quan hệ tổ hợp, không cộng cả cha lẫn con cùng lúc.

### 9.4. Đặc trưng chiến thuật hai chiều

\[
T(s,p)=ThreatValue(s,p)-ThreatValue(s,opp(p)) - [TR(s,p)-TR(s,opp(p))]
\]

`ThreatValue` chỉ tính cơ hội tấn công **chưa ghi vào Material**, phải kiểm tra nước hợp lệ và khả năng đối phương hóa giải. Cân nhắc chuẩn hóa/gộp các đặc trưng con để tránh cộng trùng với K, Q và P.

## 10. Hành quân thần tốc (Coordinated Operations)

Một lượt `CompoundAction(root_transport_id, actions=[a1,a2,a3])` hợp lệ có thể đồng thời:

1. Ăn 2–3 quân hoặc một tổ hợp nhiều quân.
2. Ăn quân mạnh bằng quân chủ lực, đồng thời dùng quân yếu tạo thế chiếu.
3. Vừa ăn quân vừa mở đường/khống chế vị trí chiến lược.
4. Ép đối phương phải giải chiếu thay vì phản công ngay — **trừ khi** đối phương có nước vừa giải chiếu vừa phản công hữu hiệu.

**Đơn vị đánh giá:**

\[
s'=T(s,a),\qquad a\in A(s),\;a\text{ là toàn bộ CompoundAction}
\]

Không gọi đánh giá từng hành động con rồi cộng điểm riêng mà bỏ qua hậu quả toàn lượt.

Để đo *synergy* chưa được Material/Position phản ánh, có thể thử đặc trưng bổ sung:

\[
CO(s,a,p)=\lambda_I Initiative(s,a,p)+\lambda_F ForcedResponse(s,a,p)+\lambda_Y SynergyResidual(s,a,p)
\]

Trong bản Heuristic **tĩnh** nên dùng `CO` để giải thích/điều chỉnh đặc trưng Tactical, không cộng thêm nguyên lợi ích ăn quân, chiếu và vị trí vốn đã có ở M/K/Q/P. Có thể so sánh một biến thể **CO on/off** bằng ablation.

**Đánh giá sau phản ứng tối ưu của đối phương (tùy chọn):**

\[
ReplyScore(s,a,p)=\min_{b\in A(s')}E_{base}(T(s',b),p)
\]

với `s'=T(s,a)` và `A(s')` là lượt hợp lệ của phe đối phương. Đây là **độ sâu 2 ply**, không phải điểm tĩnh; phải tính riêng chi phí thời gian. Nếu một lượt tổ hợp có ba hành động con thì vẫn chỉ là **1 ply**.

## 11. Công thức CCHEF tổng hợp

Khi ván chưa kết thúc:

\[
\boxed{
E_{static}(s,p)=w_M\hat M+w_K\hat K+w_Q\hat Q+w_P\hat P+w_C\hat C+w_D\hat D+w_T\hat T
}
\]

Với đặc trưng đối xứng theo góc nhìn phe `p`, ví dụ chuẩn hóa:

\[
\hat X(s,p)=\mathrm{clip}\left(\frac{X(s,p)}{scale_X},-1,1\right)
\]

`scale_X` phải xác định trước dựa trên luật hoặc tập **training**, không tính riêng theo mỗi tình huống rồi làm mất tính so sánh. `w_i ≥ 0`, `Σw_i=1` (hoặc dùng trọng số thô rồi chia tổng). Điểm thắng/thua/hòa xử lý **ngoài** tổng trên. Không có tập trọng số "chuẩn" áp dụng cho mọi ván.

**Trọng số khởi tạo để thử, chưa tối ưu:**

| Đặc trưng | M | K | Q | P | C | D | T |
|---|---:|---:|---:|---:|---:|---:|---:|
| Tỷ lệ (%) | 25 | 25 | 15 | 10 | 5 | 5 | 15 |

## 12. H1–H7: phát triển tăng dần

| Phiên bản | Đặc trưng sử dụng | Câu hỏi nghiên cứu |
|---|---|---|
| **H1** | M | Điểm quân đơn thuần hiệu quả đến đâu? |
| **H2** | M + P + C | Bày binh và cơ động có ích không? |
| **H3** | H2 + K | Phòng thủ trước thế chiếu có cải thiện không? |
| **H4** | H3 + Q | Thêm đường chiếu an toàn có ích không? |
| **H5** | H4 + D | Triển khai và vận tải cải thiện ra sao? |
| **H6** | H5 + T (gồm tổ hợp, CO/TC/TR có kiểm soát đếm trùng) | Lợi ích của chiến thuật phối hợp? |
| **H7** | H6 + trọng số theo giai đoạn ván đấu | Trọng số động tốt hơn trọng số cố định? |

- Tất cả sử dụng **cùng Game Engine, luật, danh sách hành động**, cả `CompoundAction`; chỉ khác đặc trưng/trọng số.
- Phiên bản H6 không tự động tốt hơn H5; phải chứng minh bằng kết quả.
- H7 xác định giai đoạn khai cuộc/trung cuộc/tàn cuộc bằng tiêu chí có thể tái lập (ví dụ tỷ lệ vật chất còn lại, mức triển khai), không chỉ số lượt cố định.

## 13. Grid Search tìm trọng số tốt cho từng thành phần

> **Mục tiêu:** Tìm bộ trọng số `w_M, w_K, w_Q, w_P, w_C, w_D, w_T` cho H1–H6 và (nếu đủ tài nguyên) theo từng giai đoạn H7, dựa trên **thành tích thi đấu**, không tự tuyên bố trọng số cảm tính là tối ưu.

### 13.1. Hàm mục tiêu

Với bộ trọng số `w` và tập trận đánh giá cố định:

\[
J(w)=\frac{Wins(w)+0.5\,Draws(w)}{Games(w)}
\]

Nên báo cáo thêm win/draw/loss rate, trung bình thời gian quyết định, số nút hoặc số trạng thái được đánh giá, số hành động CompoundAction, chênh lệch điểm quân cuối ván và số lỗi bất biến (phải bằng 0). Nếu hai bộ trọng số ngang hiệu quả, ưu tiên bộ ổn định giữa các seed và ít tốn thời gian hơn.

### 13.2. Tách dữ liệu để tránh overfitting

- **Tuning set:** các seed, vị trí và/hoặc đối thủ dùng để chọn trọng số.
- **Validation set:** các seed và vị trí không dùng khi điều chỉnh để chọn phiên bản.
- **Test set cuối:** giữ riêng đến khi đã khóa H1–H7 và trọng số; chỉ dùng để báo cáo kết quả cuối cùng.
- Tạo trận đối xứng: mỗi cấu hình được chơi cả **Đỏ đi trước** và **Xanh đi sau**, cùng seed/điều kiện xuất phát tương ứng.
- Dùng tập đối thủ đa dạng: Random, Rule-based, Heuristic baseline (và các agent khác nếu ổn định), tránh chỉ tối ưu để bắt nạt Random.

### 13.3. Không gian tìm kiếm Grid Search

**Không** quét mọi trọng số 0–100 bước 5 cho cả 7 thành phần cùng lúc: số tổ hợp rất lớn. Làm Grid Search **theo giai đoạn (coarse-to-fine)**.

**Vòng A — Coarse Grid Search (tối đa 3–4 nhóm trọng số):**

- H1: `w_M=1`.
- H2: chọn các tỷ lệ theo lưới đơn giản `w_M ∈ {0.4, 0.6, 0.8}`, `w_P ∈ {0.1, 0.2, 0.3}`; `w_C=1-w_M-w_P`, chỉ giữ `w_C≥0`.
- H3–H5: cố định các tỷ lệ tốt ở phiên bản trước, dành một phần ngân sách cho **đặc trưng mới**. Ví dụ `α ∈ {0, 0.1, 0.2, 0.3}` và đặt `w_new=α`, các trọng số cũ nhân `(1−α)`.
- H6: dùng nhóm trọng số `{M,K,Q,P+C+D,T}` để giảm chiều, rồi chia nhỏ nhóm vị trí/cơ động/triển khai bằng một lưới phụ.

**Vòng B — Fine Grid Search:** quanh 3–5 cấu hình có kết quả tốt nhất, quét bước nhỏ hơn (ví dụ ±0,05 sau chuẩn hóa); chỉ giữ `w_i≥0`, tổng bằng 1. Không sử dụng tập test cuối trong quá trình này.

**Ví dụ riêng cho H6:**

```yaml
heuristic: H6
initial_weights:
  M: 0.25
  K: 0.25
  Q: 0.15
  P: 0.10
  C: 0.05
  D: 0.05
  T: 0.15
coarse_alpha_new_feature: [0.0, 0.1, 0.2, 0.3]
fine_step: 0.05
selection_metric: win_points_per_game  # (wins + 0.5*draws)/games
```

**Quy tắc tinh chỉnh:** Nếu trọng số mới là `α`, thay vì cộng khiến tổng > 1:

\[
w'_{new}=\alpha,\quad w'_i=(1-\alpha)w_i^{old}
\]

### 13.4. Quy trình chạy từng ứng viên

1. Khóa phiên bản Engine, mã Evaluator, luật và seed.
2. Tạo các ứng viên từ lưới; loại ứng viên có trọng số âm/tổng sai.
3. Cho mỗi ứng viên đánh số ván thăm dò ít (ví dụ 20–40, chia đều phe) để lọc sơ bộ.
4. Đấu nhiều hơn (ví dụ 100–200 ván mỗi cấu hình vào vòng cuối) cho các ứng viên tốt nhất, tùy ngân sách tính toán.
5. So sánh theo điểm trung bình, độ biến động giữa seed, chi phí thời gian; chọn trên validation.
6. Chạy **test cuối một lần** và báo cáo kết quả, số ván cùng khoảng tin cậy nếu có thể.
7. Thực hiện **ablation**: cho trọng số của M/K/Q/P/C/D/T về 0 từng lần rồi tái chuẩn hóa để đo đóng góp từng thành phần.

**Quan trọng:** Chi phí tìm kiếm không chỉ do số trọng số; mỗi trận Cờ Tư Lệnh có thể dài và nhiều `CompoundAction`. Ưu tiên ngân sách thời gian nhất quán, lưu log và dùng cùng cấu hình phần cứng. Nếu quá tốn, lọc bằng các vị trí chiến thuật cố định trước, sau đó mới đấu đối kháng xác nhận.

### 13.5. Pseudocode Grid Search

```python
from itertools import product

def normalize(raw):
    if any(x < 0 for x in raw.values()):
        raise ValueError("negative weight")
    total = sum(raw.values())
    if total <= 0:
        raise ValueError("zero weight sum")
    return {k: v / total for k, v in raw.items()}

# Minh họa lưới H2. Không phải API thật của dự án.
candidates = []
for wm, wp in product([0.4, 0.6, 0.8], [0.1, 0.2, 0.3]):
    wc = round(1.0 - wm - wp, 10)
    if wc < 0:
        continue
    candidates.append({"M": wm, "P": wp, "C": wc})

results = []
for weights in candidates:
    # evaluate_matches() cần tự triển khai với Engine hiện tại:
    # giữ seed, đối thủ, chia phe và ngân sách trận nhất quán.
    metrics = evaluate_matches(weights=normalize(weights), split="tuning")
    results.append({"weights": weights, **metrics})

# Chỉ chọn ứng viên trên tuning/validation.
# Giữ test set cho đánh giá cuối sau khi khóa trọng số.
```

### 13.6. Grid Search cho H7 (theo giai đoạn)

Không nên mở lưới 7 trọng số × 3 giai đoạn ngay lập tức. Trước hết chốt bộ H6; sau đó khảo sát 1–2 tham số chuyển giai đoạn và vài tỷ lệ điều chỉnh nhóm trọng số như `Deployment↑` ở khai cuộc, `King Safety/Check↑` ở tàn cuộc. Có thể thử:

\[
E_{H7}(s,p)=\sum_i w_i(g(s))\hat X_i(s,p)
\]

Lựa chọn `g(s)` từ các đặc trưng quan sát được; tránh dùng thông tin tương lai. So sánh H7 với H6 cùng ngân sách.

## 14. Test tình huống bắt buộc

| ID | Tình huống | Kết quả mong đợi |
|---|---|---|
| HE-01 | Ăn Xe tăng đơn lẻ | Material cập nhật 20 điểm |
| HE-02 | Xe tăng 20 chở Dân quân 10 bị diệt | Hai quân bị loại, 30 điểm |
| HE-03 | Máy bay 40 → Xe tăng 20 → Dân quân 10 bị diệt | Tổn thất 70 điểm nếu quan hệ chở hợp lệ |
| HE-04 | Quân được phong Anh hùng | +10 Material, tầm đi theo Engine |
| HE-05 | Đối phương chiếu nhưng quân chiếu bị ăn hợp lệ/an toàn | Phạt đe dọa thấp/0 |
| HE-06 | Chiếu hết theo luật | Giá trị thắng/thua tuyệt đối |
| HE-07 | CompoundAction tiêu diệt hai quân | Đếm mỗi ID quân bị loại đúng 1 lần |
| HE-08 | Quân mạnh ăn + quân yếu chiếu | Xét phản ứng giải chiếu tốt nhất nếu bật lookahead |
| HE-09 | Vừa ăn vừa triển khai kiểm soát | Cập nhật Material/Position sau **toàn lượt** |
| HE-10 | Tổ hợp mình đang cõng bị đe dọa | TR phản ánh cả quân phụ thuộc |
| HE-11 | Máy bay vào vùng Phòng không, kết quả trì hoãn | Điểm dựa trên chuyển trạng thái/flag Engine đúng |
| HE-12 | Hoán đổi góc nhìn phe trên trạng thái đối xứng | `E(s,Đỏ)≈−E(s,Xanh)` |
| HE-13 | Nước dẫn đến lộ mặt Tư lệnh | Không nằm trong danh sách legal actions |
| HE-14 | So sánh `AtomicAction` với `CompoundAction` | Một lượt tổ hợp tính 1 ply |
| HE-15 | Cùng seed, cấu hình, Engine | Kết quả tái lập |
| HE-16 | Tắt từng thành phần trong H6 | Có bảng ablation và đánh giá riêng |

## 15. Kiến trúc gợi ý cho repository

```text
packages/
  commander_game_engine/
    ...                         # luật và chuyển trạng thái
  agents/
    base.py                     # Agent interface / Random
    rule_based.py               # ưu tiên theo luật (Agent riêng)
    heuristic.py                # Agent chọn nước theo Evaluator
    minimax.py
    alpha_beta.py
    evaluation/
      material.py
      king_safety.py
      safe_check.py
      position.py
      mobility.py
      deployment.py
      tactical.py
      evaluator.py              # tổng hợp và chuẩn hóa
      weights.py                # H1–H7 và weights
research/
  experiments/
    07_test_heuristic_agent.ipynb
  tuning/
    grid_search.py
    configs/
    results/
```

Tách `Evaluator` khỏi Agent để Minimax và Alpha-Beta dùng **cùng công thức** ở nút lá. MCTS nguyên bản có thể dùng Random Rollout; phiên bản MCTS nâng cao mới sử dụng Heuristic Rollout hoặc Leaf Evaluation. Không đánh đồng Heuristic-guided MCTS với AlphaGo: AlphaGo-inspired dùng mạng Policy/Value học được.

## 16. Ma trận thực nghiệm và báo cáo

- **Agent:** Random, Rule-based, H1–H7, Minimax, Alpha-Beta, MCTS cơ bản, MCTS-Heuristic (tùy thời gian).
- **So sánh Heuristic:** H1→H7 với đối thủ cố định; chia đều phe, số ván, seed, thời gian.
- **So sánh Search:** dùng **cùng Evaluator** và cùng độ sâu cho Minimax vs Alpha-Beta để so nút/thời gian; nếu so sức chơi dưới giới hạn thời gian cố định, ghi rõ độ sâu khác nhau.
- **So sánh MCTS:** UCT + Random Rollout vs UCT + Rule-based/Heuristic; cùng ngân sách mô phỏng **và** báo cáo thời gian thực vì chi phí rollout khác nhau.
- **Log tối thiểu:** `engine_version`, `agent_version`, `heuristic_variant`, `weights`, `normalization_scales`, `seed`, `side`, `opponent`, `result`, `num_turns`, `decision_time_ms`, `nodes_evaluated`, `material_delta`, `checks`, `compound_actions`.
- **Báo cáo:** bảng win/draw/loss, thời gian, độ biến động, nghiên cứu trường hợp các đòn chiếu/ăn tổ hợp, ablation và điểm hạn chế.

## 17. Tài liệu tham khảo và phạm vi kế thừa

1. Shannon, C. E. (1950). *Programming a Computer for Playing Chess*. Philosophical Magazine. DOI: https://doi.org/10.1080/14786445008521796 — nền tảng hàm đánh giá và tìm kiếm cờ vua.
2. Marsland, T. A. (1985). *Evaluation-Function Factors*. ICGA Journal. DOI: https://doi.org/10.3233/ICG-1985-8202 — các thành phần hàm đánh giá và trọng số.
3. Chen, J.-C., Tseng, W.-J., Wu, I.-C., & Wei, T.-H. (2020). *Comparison Training for Computer Chinese Chess*. IEEE Transactions on Games. DOI: https://doi.org/10.1109/TG.2019.2893430 — đặc trưng cờ tướng, đặc biệt Safe Potential Check.
4. Vázquez-Fernández, E., et al. (2013). *An Evolutionary Algorithm with a History Mechanism for Tuning a Chess Evaluation Function*. Applied Soft Computing. DOI: https://doi.org/10.1016/j.asoc.2013.02.015 — tối ưu trọng số, tham khảo phương pháp (không phải Grid Search trực tiếp).
5. Chen, B.-N., Liu, P.-F., Hsu, S.-C., & Hsu, T.-S. (2012). *Aggregating Consistent Endgame Knowledge in Chinese Chess*. Knowledge-Based Systems. DOI: https://doi.org/10.1016/j.knosys.2011.11.020 — tri thức tàn cuộc.
6. Stockfish (mã nguồn cổ điển): https://github.com/kobolabs/stockfish/blob/master/evaluate.cpp — tài liệu kỹ thuật, **không phải bài báo**, tham khảo King Safety và đánh giá vị trí.

**Phân biệt nguồn gốc:** Các bài báo cung cấp ý tưởng về đánh giá quân, vị trí, an toàn Tướng, các đặc trưng chiến thuật và tối ưu tham số. Các công thức `CCHEF`, `CO`, `TC/TR`, cách phối hợp Hành quân thần tốc và quy trình Grid Search trong tài liệu này là **đề xuất thiết kế và thực nghiệm cho Cờ Tư Lệnh**, không phải công thức nguyên văn được chứng minh trong các bài báo.

---

## 18. Các quyết định cần kiểm chứng trước khi hiện thực

- Điểm chính thức của **Sở chỉ huy** và cách quy đổi nếu cần chấm vật chất; Tư lệnh không chấm như quân thường.
- Quy tắc chính xác cập nhật trạng thái Anh hùng, kể cả khi các điều kiện phong Anh hùng thay đổi.
- API liệt kê các hành động của hai phe để tính `Risk`, `Mobility`, `CheckPlan` mà **không** làm sai lượt.
- Cơ chế cập nhật thương vong lập tức/trì hoãn của Máy bay và vùng Phòng không.
- Tiêu chí định nghĩa kiểm soát giao điểm (di chuyển, khả năng bắt quân hay tầm bắn) theo loại quân.
- Giới hạn độ sâu/chi phí của tactical analyzer và cách chuẩn hóa độc lập với tập test.

**Chốt hướng triển khai:** H1 (Material) → H2 (Position, Mobility) → H3 (King Safety) → H4 (Safe Check) → H5 (Deployment) → H6 (Tactical/Transport/Coordination) → H7 (phase-aware weights). Mỗi phiên bản Grid Search **coarse-to-fine**, xác nhận bằng self-play và đối thủ cố định, khóa trọng số trước khi đánh giá tập test cuối. 
