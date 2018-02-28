/* from https://www.tjvantoll.com/2015/09/13/fetch-and-errors/ */
/* Will be moved to FW main repo in FW 3.4 */
export let handleFetchErrors = function(response) {
    if (!response.ok) { throw Error(response.statusText) }
    return response
}
