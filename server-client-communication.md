_<- data sent to server_<br>
_-> data received from server_

for each uploaded file:
- <- **action** | 1B | "U"
- <- **filename length** | 1B | max 255 characters
- <- **file name** | nB | n = file name length
- <- **file size** | 8B | max 2^64 bytes
- -> **confirmation** | 1B | `0`/`1`
- `if 0:`
  - <- **file content** | nB | n = file size
  - -> **confirmation** | 1B | `0`/`1`
- `elif 1:`
  - -> **error message length** | 1B | max 255 characters
  - -> **error message** | nB | n = error message length

for each downloaded file:
- <- **action** | 1B | "U"
- <- **filename length** | 1B | max 255 characters
- <- **file name** | nB | n = file name length
- -> **confirmation** | 1B | `0`/`1`
- `if 0:`
  - -> **file size** | 8B | max 2^64 bytes
  - -> **file content** | nB | n = file size
- `elif 1:`
    - -> **error message length** | 1B | max 255 characters
    - -> **error message** | nB | n = error message length