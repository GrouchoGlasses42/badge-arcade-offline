/* Canonical addresses: EUR Ver. 1.3.0, title 0004000000153600.
 * badge_versions.py maps addresses and fields for the Ver. 1.3.1 update.
 * Works with Luma game patching.
 * Keep ownership and local SD commits in the game. HOME barriers are optional.
 * The cloud ownership request writes its signed blob to local extdata.
 */
.syntax unified
.arm
.arch armv6k
.text
.balign 4
.macro badge_path reg, target
    ldr \reg, =(\target - .Lpath\@ - 8)
.Lpath\@:
    add \reg, pc, \reg
.endm

.global badge_title_start
badge_title_start:
    push {r4, lr}
    mov r4, r0
    /* Ignore downloaded boss.sarc and its optional downloaded message flows. */
    mov r1, #2
    str r1, [r4, #0x3fc]
    str r1, [r4, #0x40c]
    mov r1, #0
    str r1, [r4, #0x400]
    str r1, [r4, #0x404]
    str r1, [r4, #0x408]
    strb r1, [r4, #0x1c0]
    strb r1, [r4, #0x1c2]
    /* The normal online path records its start time before resource loading. */
    add r0, r4, #0x410
    ldr r1, =0x42afe0
    ldr r1, [r1]
    ldr ip, =0x25ba24
    blx ip
    mov r0, #0x26
    str r0, [r4, #0x1bc]
    pop {r4, pc}

.global badge_title_resources_done
badge_title_resources_done:
    push {r4, lr}
    mov r4, r0
    bl badge_prepare_extdata
    cmp r0, #0
    beq .Ltitle_storage_failed
    mov r0, r4
    bl badge_restore_profile
    mov r0, r4
    bl badge_restore_owned
.Ltitle_storage_failed:
    cmp r0, #0
    moveq r1, #0x1d
    movne r1, #0x36
    /* Both builds bypass the intervening cloud profile download. The HOME build
     * keeps native pre-title initialization and post-round/manual export. */
    str r1, [r4, #0x1bc]
    mov r0, r1
    pop {r4, pc}

/* Bootstrap checks the archive before TitleTask exists. Prepare storage here
 * so a fresh game takes the same local-save path as an initialized game.
 * The bootstrap state owns a task pointer at +4 with the same heap fields used
 * by the native archive creator. Keep the original error dispatch after
 * preparation so real SD failures still reach the game's error handling.
 * A successful preparation already mounted the named archive: mounting that
 * name a second time fails on the native FS archive registry.
 */
.global badge_boot_prepare_extdata
badge_boot_prepare_extdata:
    push {r4, r5, r6, r7, r8, r9, r10, lr}
    mov r4, r0
    ldr r0, [r4, #4]
    bl badge_prepare_extdata
    cmp r0, #0
    movne r0, #0
    ldrne pc, =0x321084
    ldr pc, =0x321080

/* The online first-run flow normally creates the game's SD archive. Mount an
 * existing archive first; create only for the native FS not-found result range.
 * Never delete or reformat an existing archive. Keep the native archive ID,
 * quotas and mount helper. r0 is the owning task (for its heap).
 */
.global badge_prepare_extdata
badge_prepare_extdata:
    push {r4, r5, r6, lr}
    sub sp, sp, #0x48
    mov r4, r0
    mov r5, #0
    ldr r0, =0x42c94c
    ldrb r0, [r0]
    cmp r0, #0
    bne .Lextdata_ok
    ldr ip, =0x21c1e0
    blx ip
    tst r0, #0x80000000
    beq .Lextdata_ok
    and r1, r0, #0x3fc00
    cmp r1, #0x4400
    bne .Lextdata_failed
    ldr r1, =0x3ff
    and r0, r0, r1
    cmp r0, #100
    blo .Lextdata_failed
    cmp r0, #180
    bhs .Lextdata_failed
    /* Build a small local SMDH instead of loading a resource here. Bootstrap
     * can run before RomFS/catalog paths are ready, and ResourceMgr may queue
     * work on this same worker. The native create call only needs a valid SMDH.
     */
    ldr r0, =0x36c0
    ldr r1, [r4, #0xbc]
    mov r2, #0x20
    ldr ip, =0x2b9d68
    blx ip
    movs r5, r0
    beq .Lextdata_failed
    ldr r1, =0xdb0
    mov r2, #0
.Lextdata_clear_icon:
    str r2, [r0], #4
    subs r1, r1, #1
    bne .Lextdata_clear_icon
    ldr r0, =0x48444d53
    str r0, [r5]
    mov r6, #16
    add r3, r5, #8
.Lextdata_icon_title:
    badge_path r0, .Lextdata_name
    mov r1, r3
.Lextdata_icon_title_copy:
    ldrb r2, [r0], #1
    strh r2, [r1], #2
    cmp r2, #0
    bne .Lextdata_icon_title_copy
    add r3, r3, #0x200
    subs r6, r6, #1
    bne .Lextdata_icon_title
    add r0, r5, #0x2000
    mvn r1, #0x80000000
    str r1, [r0, #0x18]
    add r0, r0, #0x40
    ldr r1, =0x5a0
    ldr r2, =0x07ff07ff
.Lextdata_icon_pixels:
    str r2, [r0], #4
    subs r1, r1, #1
    bne .Lextdata_icon_pixels
    mov r2, r5
    ldr r3, =0x36c0
    mov r0, #16
    str r0, [sp]
    str r0, [sp, #4]
    ldr r0, =0x1536
    mov r1, #0
    ldr ip, =0x2ae42c
    blx ip
    tst r0, #0x80000000
    bne .Lextdata_failed
    ldr ip, =0x21c1e0
    blx ip
    tst r0, #0x80000000
    bne .Lextdata_failed
.Lextdata_ok:
    mov r0, #1
    b .Lextdata_end
.Lextdata_failed:
    mov r0, #0
.Lextdata_end:
    mov r4, r0
    cmp r5, #0
    beq .Lextdata_freed
    mov r0, r5
    ldr ip, =0x2ba5f4
    blx ip
.Lextdata_freed:
    mov r0, r4
    add sp, sp, #0x48
    pop {r4, r5, r6, pc}

.global badge_free_purchase
badge_free_purchase:
    /* Skip the shop states, then run the original post-payment finalizer.
     * It records pending plays, uploads ownership and preserves recovery.
     * Later phases still run the native helper's state-sensitive behavior.
     */
    ldrb ip, [r0]
    cmp ip, #4
    bne .Lpurchase_original
    push {r0, r1, r2, lr}
    ldr r0, =0x42b140
    ldr r0, [r0]
    ldr ip, =0x252d80
    blx ip
    mov r2, r0
    ldr r0, [sp]
    str r2, [r0, #0x48]
    str r2, [r0, #0x4c]
    mov r2, #1
    strb r2, [r0, #0x51]
    mov r1, #0xb
    ldr ip, =0x23cff8
    blx ip
    pop {r0, r1, r2, lr}
.Lpurchase_original:
    push {r4, r5, r6, r7, r8, r9, r10, r11, lr}
    ldr pc, =0x30a608

.global badge_upload_complete
badge_upload_complete:
.Lupload_complete:
    /* r1 is the native asynchronous CallContext. Preserve its mutex/event
     * handles and result object; its caller reset it before starting a request.
     * Dirty the local save so replacing cloud completion cannot suppress it.
     */
    ldr ip, =0x42b140
    ldr ip, [ip]
    mov r2, #1
    strb r2, [ip, #0x41]
    mov r2, #2
    strb r2, [r1, #0x2c]
    mov r2, #1
    str r2, [r1, #0x30]
    mov r0, #1
    bx lr

.global badge_upload_owned
badge_upload_owned:
    mov r0, #0
    b .Lupload_blob
.global badge_upload_profile
badge_upload_profile:
    cmp r3, #56
    blo .Ldownload_unavailable
    cmp r3, #0x400
    bhi .Ldownload_unavailable
    mov r0, #1
.Lupload_blob:
    push {r4, r5, r6, r7, lr}
    sub sp, sp, #12
    mov r6, r0
    mov r4, r1
    mov r5, r2
    str r3, [sp, #4]
    mov r0, #1
    mov r1, r5
    add r2, sp, #4
    badge_path r3, .Lowned_a
    cmp r6, #0
    beq .Lupload_primary_ready
    badge_path r3, .Lprofile_a
.Lupload_primary_ready:
    bl badge_file_io
    cmp r0, #0
    beq .Lowned_write_failed
    /* A second copy retains the preceding completed save if the next write
     * is interrupted. The primary is always written before the secondary. */
    mov r0, #1
    mov r1, r5
    add r2, sp, #4
    badge_path r3, .Lowned_b
    cmp r6, #0
    beq .Lupload_secondary_ready
    badge_path r3, .Lprofile_b
.Lupload_secondary_ready:
    bl badge_file_io
    mov r1, r4
    add sp, sp, #12
    pop {r4, r5, r6, r7, lr}
    b .Lupload_complete
.Lowned_write_failed:
    mov r1, r4
    add sp, sp, #12
    pop {r4, r5, r6, r7, lr}
    b .Ldownload_unavailable

.global badge_request_complete
badge_request_complete:
.Lrequest_complete:
    mov r2, #2
    strb r2, [r1, #0x2c]
    mov r2, #1
    str r2, [r1, #0x30]
    mov r0, #1
    bx lr

.global badge_download_unavailable
badge_download_unavailable:
.Ldownload_unavailable:
    /* An unexpected download must fail, never return an uninitialized buffer. */
    mov r2, #3
    strb r2, [r1, #0x2c]
    mov r2, #1
    str r2, [r1, #0x30]
    mov r0, #1
    bx lr

.global badge_return_true
badge_return_true:
    mov r0, #1
    bx lr

.global badge_return_zero
badge_return_zero:
    mov r0, #0
    bx lr

.global badge_return
badge_return:
    bx lr

/* Reject actual network operations even if an optional online menu reaches
 * them. These SDK routines return nn::Result, with untouched output buffers
 * on failure. Use each module's native NotInitialized result encoding.
 */
.global badge_http_unavailable
badge_http_unavailable:
    ldr r0, =0xd8a0a3f8
    bx lr

.global badge_soc_unavailable
badge_soc_unavailable:
    ldr r0, =0xd8a073f8
    bx lr

/* The base RomFS schedule expires in 2030. Its native lookup already has an
 * ignore-dates option. Use it for this bundled schedule, leaving other
 * schedule objects and the console's clock alone.
 */
.global badge_schedule_lookup
badge_schedule_lookup:
    ldr ip, =0x42ae68
    ldr ip, [ip]
    add ip, ip, #0x70000
    ldr ip, [ip, #0xdf4]
    cmp r0, ip
    moveq r3, #1
    push {r0, r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, lr}
    ldr pc, =0x258b84

.global badge_boss_register_complete
badge_boss_register_complete:
    mov r1, #2
    strb r1, [r0, #0x4e]
    bx lr

/* First-time dialogue has its own identity/login commands, independent of
 * the title and gameplay request controller. Complete their local state so
 * the tutorial can finish and create the save without contacting ACT/NEX.
 */
.global badge_identity_complete
badge_identity_complete:
    ldr ip, [r0, #0x10]
    add ip, ip, #0x400
    mov r1, #2
    str r1, [ip, #0xd4]
    bx lr

/* SaveDataMgr refuses to snapshot a save when the local ACT persistent ID is
 * zero. Preserve a cached account ID; use 1 for an unlinked offline profile.
 * The same native getter is used to validate the account field when loading.
 */
.global badge_persistent_id
badge_persistent_id:
    push {r4, lr}
    bl .Lpersistent_id_original
    cmp r0, #0
    moveq r0, #1
    pop {r4, pc}
.Lpersistent_id_original:
    push {r3, r4, r5, r6, r7, lr}
    ldr pc, =0x28fbb0

/* Transfer a signed native ownership blob through the game's extdata device.
 * r0: read=0/write=1, r1: blob buffer, r2: length pointer, r3: relative filename.
 * A fixed-size file holds a magic, a bounded length and the original signed
 * blob. The original decoder verifies its signature before changing ownership.
 */
.global badge_file_io
badge_file_io:
    push {r4, r5, r6, r7, r8, r9, r10, r11, lr}
    sub sp, sp, #0x54
    mov r4, r0
    mov r5, r1
    mov r6, r2
    mov r7, r3
    mov r10, #0
    /* Reject invalid writes before opening or changing either saved copy. */
    cmp r4, #1
    bne .Lfile_prepare
    ldr r0, [r6]
    cmp r0, #0x20
    bls .Lfile_end
    ldr r1, =0x499ea
    cmp r0, r1
    bhi .Lfile_end
.Lfile_prepare:
    mov r0, #0
    mov r1, #0
    str r0, [sp]
    add r2, sp, #8
    mov r3, #12
.Lclear_file:
    str r0, [r2], #4
    subs r3, r3, #1
    bne .Lclear_file
    ldr r0, =0x40d714
    str r0, [sp, #8]
    ldr r0, =0x40e038
    str r0, [sp, #0x38]
    str r7, [sp, #0x3c]
    ldr r0, =0x44f790
    ldr r0, [r0]
    mov r1, #2
    ldr ip, =0x25acd4
    blx ip
    mov r8, r0
    cmp r8, #0
    beq .Lfile_end
.Lfile_open:
    mov r0, r8
    add r1, sp, #8
    add r2, sp, #0x38
    mov r3, r4
    ldr ip, =0x2704b8
    blx ip
    movs r9, r0
    bne .Lfile_transfer
    cmp r4, #1
    bne .Lfile_end
    /* extdata files must be created explicitly before opening for writing. */
    ldr r0, =0x42b140
    ldr r0, [r0]
    mov r1, r7
    ldr r2, =0x499f2
    mov r3, #0
    ldr ip, =0x25a684
    blx ip
    cmp r0, #0
    beq .Lfile_end
    mov r0, r8
    add r1, sp, #8
    add r2, sp, #0x38
    mov r3, #1
    ldr ip, =0x2704b8
    blx ip
    movs r9, r0
    beq .Lfile_end
.Lfile_transfer:
    ldr r11, =0x271de4
    cmp r4, #0
    beq .Lfile_header
    ldr r0, =0x464f4142
    str r0, [sp, #0x40]
    ldr r0, [r6]
    str r0, [sp, #0x44]
    ldr r11, =0x2703bc
.Lfile_header:
    mov r0, #8
    str r0, [sp]
    mov r0, r9
    add r1, sp, #0x48
    add r2, sp, #8
    add r3, sp, #0x40
    blx r11
    cmp r0, #0
    beq .Lfile_close
    ldr r0, [sp, #0x48]
    cmp r0, #8
    bne .Lfile_close
    ldr r0, [sp, #0x40]
    ldr r1, =0x464f4142
    cmp r0, r1
    bne .Lfile_close
    ldr r7, [sp, #0x44]
    cmp r7, #0x20
    bls .Lfile_close
    ldr r0, =0x499ea
    cmp r7, r0
    bhi .Lfile_close
    str r7, [sp]
    mov r0, r9
    add r1, sp, #0x48
    add r2, sp, #8
    mov r3, r5
    blx r11
    cmp r0, #0
    beq .Lfile_close
    ldr r0, [sp, #0x48]
    cmp r0, r7
    bne .Lfile_close
    str r7, [r6]
    mov r10, #1
.Lfile_close:
    mov r0, r9
    add r1, sp, #8
    ldr ip, =0x271efc
    blx ip
    cmp r0, #0
    moveq r10, #0
.Lfile_end:
    mov r0, r10
    add sp, sp, #0x54
    pop {r4, r5, r6, r7, r8, r9, r10, r11, pc}

/* Restore the signed native free-play/profile blob. Its setup stage is
 * separate from ownership and local story flags. Keep the native stage setter
 * (0x246cc0); only redirect its upload. Otherwise the tutorial restarts forever.
 */
.global badge_restore_profile
badge_restore_profile:
    push {r4, r5, r6, lr}
    sub sp, sp, #8
    ldr r4, [r0, #0x264]
    mov r5, #0
.Lprofile_try:
    mov r0, #0
    mov r1, r4
    add r2, sp, #4
    cmp r5, #0
    bne .Lprofile_secondary
    badge_path r3, .Lprofile_a
    b .Lprofile_path_ready
.Lprofile_secondary:
    badge_path r3, .Lprofile_b
.Lprofile_path_ready:
    bl badge_file_io
    cmp r0, #0
    beq .Lprofile_next
    ldr r2, [sp, #4]
    cmp r2, #56
    blo .Lprofile_next
    cmp r2, #0x400
    bhi .Lprofile_next
    ldr r0, [r4, #4]
    cmp r0, #2
    bhi .Lprofile_next
    ldr r0, =0x42ae68
    ldr r0, [r0]
    mov r1, r4
    ldr ip, =0x2eacc0
    blx ip
    cmp r0, #0
    bne .Lprofile_end
.Lprofile_next:
    add r5, r5, #1
    cmp r5, #2
    blo .Lprofile_try
    /* Existing stock saves already record completed local setup. */
    ldr r0, =0x42b140
    ldr r0, [r0]
    mov r1, #5
    ldr ip, =0x259680
    blx ip
    cmp r0, #0
    moveq r1, #0
    movne r1, #2
    ldr r0, =0x42ae68
    ldr r0, [r0]
    add r0, r0, #0x70000
    str r1, [r0, #0xe00]
.Lprofile_end:
    mov r0, #1
    add sp, sp, #8
    pop {r4, r5, r6, pc}

/* Called after the base resources have been initialized. */
.global badge_restore_owned
badge_restore_owned:
    push {r4, r5, r6, lr}
    sub sp, sp, #8
    ldr r4, [r0, #0x264]
    mov r5, #0
.Lrestore_try:
    mov r0, #0
    mov r1, r4
    add r2, sp, #4
    cmp r5, #0
    bne .Lrestore_secondary
    badge_path r3, .Lowned_a
    b .Lrestore_path_ready
.Lrestore_secondary:
    badge_path r3, .Lowned_b
.Lrestore_path_ready:
    bl badge_file_io
    cmp r0, #0
    beq .Lrestore_next
    ldr r0, =0x42ae68
    ldr r0, [r0]
    mov r1, r4
    ldr r2, [sp, #4]
    ldr ip, =0x23952c
    blx ip
    cmp r0, #0
    bne .Lrestore_ok
.Lrestore_next:
    add r5, r5, #1
    cmp r5, #2
    blo .Lrestore_try
.Lrestore_ok:
    /* No cache is a fresh in-game collection. Never import HOME/GYTB data. */
    mov r0, #1
    add sp, sp, #8
    pop {r4, r5, r6, pc}

/* Keep the callers' native save/profile transitions, without queuing the
 * destructive HOME export worker or touching HOME's archive at all.
 */
.global badge_home_complete
badge_home_complete:
    ldr r1, [r0, #0x3c]
    mov r0, #0
    strb r0, [r1, #0xc8]
    strb r0, [r1, #0xc9]
    strb r0, [r1, #0xca]
    str r0, [r1, #0xcc]
    mov r0, r1
    /* Finish the native saving overlay and APT sleep guard as well. */
    ldr ip, =0x244e84
    bx ip

.global badge_home_result
badge_home_result:
    mov r1, #0
    str r1, [r0]
    bx lr

/* HOME registration markers are absent. Owned counts still come from the
 * game's signed collection; custom HOME badges are neither read nor changed.
 */
.global badge_home_query
badge_home_query:
    mov r1, #0
    cmp r2, #0
    strne r1, [r2]
    str r1, [r0]
    bx lr

.global badge_home_has_collection
badge_home_has_collection:
    mov r1, #0
    cmp r2, #0
    strbne r1, [r2]
    str r1, [r0]
    bx lr

.global badge_home_categories
badge_home_categories:
    mov r0, #0
    cmp r3, #0
    bxeq lr
.Lhome_category_loop:
    strb r0, [r1], #1
    subs r3, r3, #1
    bne .Lhome_category_loop
    bx lr

/* Defense at the SDK archive boundary, including its create/reformat helper.
 * Any unhandled HOME operation fails before issuing filesystem IPC.
 */
.global badge_home_unavailable
badge_home_unavailable:
    mov r0, #8
    bx lr

/* HOME decoration no longer exists in this build. Skip only that lesson,
 * retaining the first crane tutorial and every other native story predicate.
 */
.global badge_story_flag
badge_story_flag:
    cmp r1, #4
    moveq r0, #1
    bxeq lr
    asr r2, r1, #5
    ldr pc, =0x259684

/* The bootstrap checks HOME files before TitleTask starts, independently of
 * the export SDK. Complete only BADGE:/ checks through their native success
 * callback. Keep the same shared checker intact for the game's own saves.
 */
.global badge_home_boot_check
badge_home_boot_check:
    push {r0, r1, r2, r3, ip, lr}
    ldr ip, [r0]
    ldr ip, [ip, #0x28]
    blx ip
    cmp r0, #0
    beq .Lboot_check_original
    ldr r1, [r0]
    ldr r2, =0x47444142
    cmp r1, r2
    bne .Lboot_check_original
    ldrb r1, [r0, #4]
    cmp r1, #69
    ldrbeq r1, [r0, #5]
    cmpeq r1, #58
    bne .Lboot_check_original
    pop {r0, r1, r2, r3, ip, lr}
    ldr ip, [r0]
    ldr ip, [ip, #0x2c]
    bx ip
.Lboot_check_original:
    pop {r0, r1, r2, r3, ip, lr}
    push {r4, r5, r6, r7, r8, r9, r10, r11, lr}
    ldr pc, =0x32260c

.balign 4
.Lextdata_name: .asciz "Badge Arcade Offline"
.Lowned_a: .asciz "ba_owned_a.dat"
.Lowned_b: .asciz "ba_owned_b.dat"
.Lprofile_a: .asciz "ba_prof_a.dat"
.Lprofile_b: .asciz "ba_prof_b.dat"
.balign 4

.ltorg
