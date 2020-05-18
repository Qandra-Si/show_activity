# show_activity
Сбор информации о регионе eveonline (о системе, о констелляции, о домене) при подготовке к переезду из региона в регион, для проверки региона на предмет кто в нём живёт, охотится, крабит. Генератор не пригоден для сбора данных по `hi-sec` и по `claim-00` регионам, основное предназначение сборщика данных это анализ `low-sec` и `npc-00` регионов, на основе собранных статистических данных по PvP-активности с серверов (zKillboard)[https://zkillboard.com/] и (CPP)(https://developers.eveonline.com/resource/resources). Руководителям альянсов и корпораций инструмент может быть полезен для сбора аналитики об удержании планетных систем (регионов проживания) пилотами корпораций, в условиях когда именно PvP-составляющая является основным критерием удержания региона, а не наличие в регионах посторонних структур (нередко заброшенных).

Пример собранной информации по констелляциям `Fabai`, `Leseasesh`, `Maal`: [aridia.html](https://qandra-si.github.io/show_activity/docs/index.html). 

Скрипт генерирует html-страницу с данными о наиболее опасных системах в регионе, со сведениями о пилотах.

<img src="https://raw.githubusercontent.com/Qandra-Si/show_activity/master/examples/example.png" height="60%" width="60%">

Генерируемая страница является целостным документом, который можно переносить одним файлом. В html-страницу встроена возможность фильтрации имён пилотов, для быстрого получения информации о персонажах, присутствующих в локале.

<img src="https://raw.githubusercontent.com/Qandra-Si/show_activity/master/examples/filter.png" height="60%" width="60%">
