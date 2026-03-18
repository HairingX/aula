# Aula API v23 Reference

Reference documentation for the Aula v23 API and Meebook widget APIs, captured from live traffic on 2026-03-18.

Base URL: `https://www.aula.dk/api/v23/?method=<module>.<method>`

All responses follow a common envelope:

```json
{
  "status": { "code": 0, "message": "OK" },
  "data": ...,
  "version": 23,
  "module": "<module>",
  "method": "<method>"
}
```

---

## Table of Contents

- [Profiles](#profiles)
- [Calendar](#calendar)
- [Messaging](#messaging)
- [Notifications](#notifications)
- [Presence](#presence)
- [Gallery](#gallery)
- [Posts](#posts)
- [Groups](#groups)
- [Consents](#consents)
- [Municipal Configuration](#municipal-configuration)
- [Calendar Feed](#calendar-feed)
- [Aula Tokens (Widgets)](#aula-tokens-widgets)
- [Meebook APIs](#meebook-apis)
- [Shared Types](#shared-types)

---

## Profiles

### profiles.getProfilesByLogin

Returns the logged-in user's profiles and children.

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | none |

**Response** `data`:

```
{
  profiles: [{
    institutionProfiles: [InstitutionProfileFull],  // guardian's profiles per institution
    children: [{
      institutionProfile: InstitutionProfileFull,    // child's profile
      id: int                                        // profileId
    }],
    id: int                                          // profileId
  }]
}
```

`InstitutionProfileFull`:

| Property | Type | Description |
|---|---|---|
| `id` | int | Institution profile ID (instProfileId) |
| `profileId` | int | Cross-institution profile ID |
| `institutionCode` | string | e.g. "791006", "G16713" |
| `institutionName` | string | |
| `municipalityCode` | string | e.g. "791" |
| `municipalityName` | string | e.g. "Viborg" |
| `firstName` | string | |
| `lastName` | string | |
| `fullName` | string | |
| `gender` | string | "M" / "F" |
| `role` | string | "guardian" / "child" / "employee" |
| `institutionRole` | string\|null | "guardian", "early-student", "daycare", etc. |
| `institutionType` | string\|null | "School", "Daycare" |
| `aulaEmail` | string\|null | |
| `address` | [Address](#address) | |
| `email` | string\|null | |
| `homePhoneNumber` | string\|null | |
| `mobilePhoneNumber` | string\|null | |
| `workPhoneNumber` | string\|null | |
| `mainGroup` | [GroupBrief](#groupbrief)\|null | Only populated in some contexts |
| `shortName` | string | Initials, e.g. "PHDN" |
| `profilePictureUrl` | string\|null | Deprecated, always null |
| `profilePicture` | [ProfilePicture](#profilepicture)\|null | |
| `newInstitutionProfile` | bool | |
| `communicationBlocked` | bool\|null | |
| `isPrimary` | bool\|null | Primary institution for user |
| `birthday` | string\|null | ISO 8601 datetime |
| `institutionProfileDescriptions` | any\|null | |
| `lastActivity` | string\|null | |
| `hasCustody` | bool\|null | |
| `alias` | bool | |
| `groups` | array\|null | |
| `relation` | string\|null | "Far", "Mor", etc. |
| `isInternalProfilePicture` | bool\|null | |
| `accessLevel` | int\|null | 1 = full access |
| `currentUserCanViewContactInformation` | bool | |
| `userHasGivenConsentToShowContactInformation` | bool | |
| `deactivated` | bool\|null | |
| `profileStatus` | string | "active" |
| `currentUserCanSeeProfileDescription` | bool | |
| `currentUserCanEditProfileDescription` | bool | |
| `currentUserCanEditContactInformation` | bool | |
| `currentUserCanEditProfilePicture` | bool | |
| `currentUserCanDeleteProfilePicture` | bool | |
| `shouldShowDeclineConsentTwoWarning` | bool\|null | |
| `contactType` | string | "profile" |
| `hasBlockedCommunicationChannels` | bool | |
| `metadata` | string | Context string, e.g. "Milas 1A" |

---

### profiles.getProfileContext

Returns detailed profile context including institutions, widgets, permissions, and children.

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | none |

**Response** `data`:

| Property | Type | Description |
|---|---|---|
| `id` | int | profileId |
| `userId` | string | Unilogin ID |
| `portalRole` | string | "guardian" / "employee" |
| `supportRole` | bool | |
| `municipalAdmin` | bool | |
| `isGroupHomeAdmin` | bool | |
| `institutionProfile` | object | See below |

`institutionProfile`:

| Property | Type | Description |
|---|---|---|
| `encryptionKey` | string | SHA1 key |
| `communicationBlock` | bool | |
| `address` | [Address](#address) | |
| `email` | string | |
| `birthday` | string | ISO 8601 |
| `phone` | string | |
| `delegatedCalendarProfiles` | array | |
| `relations` | [InstitutionProfileBrief] | Children's profiles |

The response also contains `institutions` array with widgets, groups, and permissions per institution (large nested structure).

---

### profiles.getProfileMasterData

Returns master data for specific institution profile IDs, including relations and contact info.

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `instProfileIds[]=<int>` |

**Response** `data`:

| Property | Type | Description |
|---|---|---|
| `institutionProfiles` | array | Profiles with relations (same as InstitutionProfileFull but with `relations` array of children) |
| `children` | array | |
| `age18AndOlder` | bool\|null | |
| `overConsentAge` | bool | |
| `contactInfoEditable` | bool\|null | |
| `isInternalProfilePicture` | bool | |
| `profileId` | int | |
| `displayName` | string | |

---

### profiles.getAnyUnansweredAdditionalDataResponsesForOwner

| | |
|---|---|
| **HTTP** | `GET` |
| **Response** | `data: bool` |

---

### profiles.getContactlist

Returns contact list for a group.

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `groupId`, `filter` ("child"), `field` ("name"), `page`, `order` ("asc") |

**Response** `data`: array of contacts, each being an InstitutionProfileFull with added `relations` array containing guardian profiles.

Extra contact list properties:

| Property | Type | Description |
|---|---|---|
| `relations` | array | Guardian/parent profiles |
| `groupHomeId` | int\|null | |

---

## Calendar

### calendar.getEventsByProfileIdsAndResourceIds

Returns lesson schedule and events for given profiles and date range.

| | |
|---|---|
| **HTTP** | `POST` |
| **Body** | `{ instProfileIds: [int], start: string, end: string }` |

Date format: `"2026-03-18 00:00:00.0000+01:00"`

**Response** `data`: array of [CalendarEvent](#calendarevent)

`CalendarEvent`:

| Property | Type | Description |
|---|---|---|
| `id` | int | Event ID |
| `title` | string | Event/lesson title |
| `allDay` | bool | |
| `startDateTime` | string | ISO 8601 |
| `endDateTime` | string | ISO 8601 |
| `oldStartDateTime` | string\|null | Previous time (if changed) |
| `oldEndDateTime` | string\|null | |
| `oldAllDay` | bool\|null | |
| `responseRequired` | bool | |
| `private` | bool | |
| `type` | string | "lesson", "event", "presence_holiday", "holiday", "birthday", "excursion", "other", "school_home_meeting", "parental_meeting", "performance_meeting" |
| `primaryResourceText` | string\|null | |
| `additionalResources` | array | |
| `additionalResourceText` | string\|null | |
| `repeating` | any\|null | |
| `institutionCode` | string\|null | |
| `institutionName` | string\|null | |
| `addedToInstitutionCalendar` | bool | |
| `creatorInstProfileId` | int\|null | |
| `creatorProfileId` | int\|null | |
| `creatorName` | string\|null | |
| `invitedGroups` | [[GroupDetailed](#groupdetailed)] | |
| `primaryResource` | `{ id: int, name: string }\|null` | Room/location |
| `hasAttachments` | bool | |
| `createdDateTime` | string | ISO 8601 |
| `lesson` | [Lesson](#lesson)\|null | Only for type "lesson" |
| `timeSlot` | any\|null | |
| `vacationChildrenCountByDates` | any\|null | |
| `belongsToProfiles` | [int] | instProfileIds this event belongs to |
| `belongsToResources` | [int] | |
| `requiresNewAnswer` | bool | |
| `directlyRelated` | bool | |
| `responseDeadline` | string\|null | ISO 8601 |
| `responseStatus` | string\|null | "waiting" / null |

`Lesson`:

| Property | Type | Description |
|---|---|---|
| `lessonId` | string | UUID |
| `lessonStatus` | string | "normal" |
| `participants` | array | See below |
| `hasRelevantNote` | bool | |

`LessonParticipant`:

| Property | Type | Description |
|---|---|---|
| `teacherId` | int | |
| `teacherName` | string | |
| `teacherInitials` | string | |
| `participantRole` | string | "primaryTeacher" |

---

### calendar.getEventTypes

Returns all available event types for given institutions.

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `filterInstitutionCodes[]=<string>` |

**Response** `data`: `string[]`

Known values: `"event"`, `"holiday"`, `"presence_holiday"`, `"birthday"`, `"excursion"`, `"other"`, `"school_home_meeting"`, `"parental_meeting"`, `"performance_meeting"`, `"lesson"`

---

### calendar.getBirthdayEventsForInstitutions

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `start`, `end` (ISO 8601 with tz offset), `instCodes[]=<string>` |

**Response** `data`: array of:

| Property | Type | Description |
|---|---|---|
| `institutionProfileId` | int | |
| `birthday` | string | ISO 8601 |
| `institutionCode` | string | |
| `name` | string | Full name |
| `mainGroupName` | string | e.g. "1A" |
| `relatedChildrenIds` | [int] | instProfileIds of your related children |

---

### calendar.getImportantDates

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `limit=<int>`, `include_today=<bool>` |

**Response** `data`: array of [CalendarEvent](#calendarevent) (same shape as getEventsByProfileIdsAndResourceIds)

---

## Messaging

### messaging.getThreads

Returns paginated thread list.

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `sortOn` ("date"), `orderDirection` ("desc"), `page` (0-based) |

**Response** `data`:

| Property | Type | Description |
|---|---|---|
| `moreMessagesExist` | bool | More pages available |
| `page` | int | Current page |
| `threads` | [Thread] | |

`Thread`:

| Property | Type | Description |
|---|---|---|
| `id` | int | Thread ID |
| `subject` | string | |
| `leaveTime` | string\|null | |
| `latestMessage` | object | `{ id, sendDateTime, text: { html } }` (truncated preview) |
| `regardingChildren` | array | `[{ profilePicture, shortName, profileId, displayName }]` |
| `creator` | [MessageSender](#messagesender) | |
| `startedTime` | string | ISO 8601 |
| `read` | bool | |
| `isThreadOrSubscriptionDeleted` | bool | |
| `subscriptionId` | int | |
| `subscriptionType` | string | "unbundled" |
| `numberOfBundleItems` | int\|null | |
| `primarySubscriptionId` | int\|null | |
| `threadEntityLinkDto` | object\|null | `{ entityId: int, threadType: string }` |
| `folderId` | int\|null | |
| `folderType` | string | "normal" |
| `recipients` | [ThreadRecipient] | |
| `extraRecipientsCount` | int\|null | |
| `muted` | bool | |
| `marked` | bool | |
| `sensitive` | bool | |
| `lastReadMessageId` | string | |
| `isArchived` | bool | |
| `mailBoxOwner` | [MailBoxOwner](#mailboxowner) | |
| `institutionCode` | string | |

Known `threadType` values: `"vacation_request_reminder"`

`ThreadRecipient`:

| Property | Type | Description |
|---|---|---|
| `lastReadMessageId` | string | |
| `lastReadTimestamp` | string | ISO 8601 |
| `leaveTime` | string\|null | |
| `deletedAt` | string\|null | |
| `shortName` | string | |
| `profilePicture` | [ProfilePicture](#profilepicture) | |
| `mailBoxOwner` | [MailBoxOwner](#mailboxowner) | |
| `fullName` | string | |
| `metadata` | string | |
| `answerDirectlyName` | string | |

---

### messaging.getMessagesForThread

Returns messages for a specific thread.

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `threadId=<int>`, `page=<int>` |

**Response** `data`:

| Property | Type | Description |
|---|---|---|
| `messages` | [Message] | |
| `firstMessage` | Message | |
| `threadCreator` | [MessageSender](#messagesender) | |
| `threadStartedDateTime` | string | ISO 8601 |
| `isThreadForwarded` | bool | |
| `moreMessagesExist` | bool | |
| `hasSecureDocuments` | bool | |
| `page` | int | |
| `totalMessageCount` | int | |
| `threadEntityLinkDto` | object\|null | `{ entityId, threadType }` |

`Message`:

| Property | Type | Description |
|---|---|---|
| `id` | string | Message ID (format: "hex.hex") |
| `sendDateTime` | string | ISO 8601 |
| `deletedAt` | string\|null | |
| `text` | object | `{ html: string }` |
| `hasAttachments` | bool | |
| `pendingMedia` | bool | |
| `messageType` | string | "Message" |
| `leaverNames` | string\|null | |
| `inviterName` | string\|null | |
| `sender` | [MessageSender](#messagesender) | |
| `newRecipients` | any\|null | |
| `originalRecipients` | any\|null | |
| `attachments` | array\|null | |
| `canReplyToMessage` | bool | |

---

### messaging.getNewThreads

Poll for new threads since a timestamp.

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `lastPollingTimestamp` (ISO 8601), `page` |

**Response** `data`: `{ moreMessagesExist: bool, page: int, threads: [] }`

---

### messaging.getFolders

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `includeDeletedFolders=<bool>` |

**Response** `data`: array of:

| Property | Type | Description |
|---|---|---|
| `id` | int | |
| `name` | string | e.g. "Slettet post" |
| `type` | string | "deleted" |
| `commonInboxName` | string\|null | |

---

### messaging.getCommonInboxes

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `institutionProfileIds[]=<int>` |

**Response** `data`: `[]` (empty array observed)

---

### messaging.setLastReadMessage

Mark a message as read.

| | |
|---|---|
| **HTTP** | `POST` |
| **Body** | `{ threadId: int, messageId: string, commonInboxId: int\|null, otpInboxId: int\|null }` |

**Response** `data`: `null`

---

## Notifications

### notifications.getNotificationsForActiveProfile

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `activeChildrenIds[]=<int>`, `activeInstitutionCodes[]=<string>` |

**Response** `data`: `[]` (empty in captured session)

---

### Notifications.deleteNotifications

| | |
|---|---|
| **HTTP** | `POST` |
| **Body** | `{ notifications: [] }` |

**Response** `data`: `null`

---

## Presence

### presence.getDailyOverview

Returns today's presence status for children.

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `childIds[]=<int>` (instProfileIds) |

**Response** `data`: array of:

| Property | Type | Description |
|---|---|---|
| `id` | int | Overview ID |
| `institutionProfile` | [InstitutionProfileBrief](#institutionprofilebrief) | Child's profile |
| `mainGroup` | [GroupDetailed](#groupdetailed) | |
| `status` | int | Presence state code (see [Presence States](#presence-state-codes)) |
| `location` | string\|null | |
| `sleepIntervals` | array | |
| `checkInTime` | string\|null | "HH:MM:SS" format |
| `checkOutTime` | string\|null | "HH:MM:SS" format |
| `editablePresenceStates` | array | |
| `isDefaultEntryTime` | bool | |
| `isDefaultExitTime` | bool | |
| `isPlannedTimesOutsideOpeningHours` | bool | |
| `vacationNote` | string\|null | |
| `activityType` | int | 0 = normal |
| `entryTime` | string\|null | Planned entry "HH:MM:SS" |
| `exitTime` | string\|null | Planned exit "HH:MM:SS" |
| `exitWith` | string\|null | Who picks up, e.g. "Bedsteforældre" |
| `comment` | string\|null | |
| `spareTimeActivity` | any\|null | |
| `selfDeciderStartTime` | string\|null | |
| `selfDeciderEndTime` | string\|null | |

#### Presence State Codes

| Code | Meaning |
|---|---|
| `8` | Checked out |

(Other codes not observed in this capture)

---

### presence.getPresenceStates

Returns current presence state per child.

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `institutionProfileIds[]=<int>` |

**Response** `data`: array of:

| Property | Type | Description |
|---|---|---|
| `uniStudentId` | int | instProfileId |
| `uniStudent` | [InstitutionProfileBrief](#institutionprofilebrief) | |
| `state` | int | Presence state code |

---

### presence.getPresenceConfigurationByChildIds

Returns presence module configuration per child.

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `childIds[]=<int>` |

**Response** `data`: array of:

| Property | Type | Description |
|---|---|---|
| `uniStudentId` | int | |
| `presenceConfiguration` | object | See below |

`presenceConfiguration`:

| Property | Type | Description |
|---|---|---|
| `institution` | object | `{ institutionCode, name }` |
| `goHomeWith` | bool | Feature enabled |
| `selfDecider` | bool | Feature enabled |
| `sendHome` | bool | Feature enabled |
| `pickup` | bool | Feature enabled |
| `departments` | array | Department groups with filteringGroups |
| `dashboardModuleSettings` | array | Per-context module permissions |

`dashboardModuleSettings` item:

| Property | Type | Description |
|---|---|---|
| `presenceDashboardContext` | string | "employee_dashboard", "check_in_dashboard", "guardian_dashboard" |
| `presenceModules` | array | Module permissions |

`presenceModule`:

| Property | Type | Description |
|---|---|---|
| `moduleType` | string | "location", "sleep", "field_trip", "spare_time_activity", "vacation", "daily_message", "report_sick", "drop_off_time", "pickup_times", "pickup_type" |
| `permission` | string | "deactivated", "readable", "editable" |

---

### presence.getPresenceTemplates

Returns weekly schedule templates per child.

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `filterInstitutionProfileIds[]=<int>`, `fromDate`, `toDate` (YYYY-MM-DD) |

**Response** `data`:

| Property | Type | Description |
|---|---|---|
| `currentDate` | string | YYYY-MM-DD |
| `presenceWeekTemplates` | array | Per-child templates |

`presenceWeekTemplate`:

| Property | Type | Description |
|---|---|---|
| `institutionProfile` | [InstitutionProfileBrief](#institutionprofilebrief) | |
| `dayTemplates` | [DayTemplate] | |

`DayTemplate`:

| Property | Type | Description |
|---|---|---|
| `id` | int | |
| `dayOfWeek` | int | 1=Monday ... 5=Friday |
| `byDate` | string | YYYY-MM-DD |
| `repeatPattern` | string | "weekly" / "never" |
| `repeatFromDate` | string | ISO 8601 |
| `repeatToDate` | string\|null | |
| `isOnVacation` | bool | |
| `vacation` | object\|null | |
| `isPlannedTimesOutsideOpeningHours` | bool | |
| `isDefaultEntryTime` | bool | |
| `isDefaultExitTime` | bool | |
| `activityType` | int | |
| `entryTime` | string | "HH:MM:SS" |
| `exitTime` | string | "HH:MM:SS" |
| `exitWith` | string | |
| `comment` | string | |
| `spareTimeActivity` | any\|null | |
| `selfDeciderStartTime` | string\|null | |
| `selfDeciderEndTime` | string\|null | |

---

### presence.getOpeningHoursByInstitutionCodes

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `institutionCodes[]=<string>`, `startDate`, `endDate` (YYYY-MM-DD) |

**Response** `data`:

```
{
  openingHoursOverviewDto: [{
    institutionCode: string,
    openingHoursDto: [{
      institutionCode: string,
      date: string,           // "YYYY-MM-DD"
      openTime: string,       // "HH:MM"
      closeTime: string,      // "HH:MM"
      type: string,           // "general_opening_hours"
      name: string|null
    }]
  }]
}
```

---

### presence.getGeneralOpeningHours

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `institutionCodes[]=<string>` |

**Response** `data`:

```
{
  institutionOpeningHours: [{
    institutionCode: string,
    openingHours: [{
      institutionCode: string,
      dayOfWeek: int,          // 1-5 (Mon-Fri)
      openTime: string,        // "HH:MM"
      closeTime: string        // "HH:MM"
    }]
  }]
}
```

---

### presence.getSpecificOpeningHourOverview

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `institutionCodes[]=<string>` |

**Response** `data`: `{ specificOpeningHoursWithInstitutions: [] }`

---

### presence.getClosedDays

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `institutionCodes[]=<string>` |

**Response** `data`:

```
{
  institutionClosedDays: [{
    institutionCode: string,
    closedDaysOverview: {
      closedDays: [{
        id: int,
        startDate: string,     // "YYYY-MM-DD"
        endDate: string,       // "YYYY-MM-DD"
        name: string           // e.g. "Jul og nytår"
      }]
    }
  }]
}
```

---

### presence.getPickupResponsibles

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `uniStudentIds[]=<int>` (instProfileIds) |

**Response** `data`: array of:

| Property | Type | Description |
|---|---|---|
| `uniStudentId` | int | |
| `relatedPersons` | array | `[{ institutionProfileId, name, relation, groupHomeId }]` |
| `pickupSuggestions` | array | `[{ id, uniStudentId, pickupName }]` |

---

### presence.getVacationAnnouncementsByChildren

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `childIds[]=<int>` |

**Response** `data`: `[]` (empty in capture)

---

### presence.getVacationRegistrationsByChildren

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `childIds[]=<int>` |

**Response** `data`: array of:

| Property | Type | Description |
|---|---|---|
| `child` | [InstitutionProfileBrief](#institutionprofilebrief) | |
| `vacationRegistrations` | [VacationRegistration] | |

`VacationRegistration`:

| Property | Type | Description |
|---|---|---|
| `vacationRegistrationId` | int | |
| `startDate` | string | "YYYY-MM-DD" |
| `endDate` | string | "YYYY-MM-DD" |
| `title` | string | |
| `noteToGuardian` | string | |
| `responseId` | int | |
| `responseDeadline` | string | "YYYY-MM-DD" |
| `isEditable` | bool | |
| `isMissingAnswer` | bool | |
| `isPresenceTimesRequired` | bool | |

---

## Gallery

### gallery.getAlbums

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `index`, `limit`, `sortOn` ("mediaCreatedAt"), `orderDirection` ("desc"), `filterBy` ("all"), `filterInstProfileIds[]=<int>` |

**Response** `data`: array of:

| Property | Type | Description |
|---|---|---|
| `id` | int | Album ID |
| `title` | string | |
| `description` | string | |
| `creator` | [Creator](#creator) | |
| `creationDate` | string | ISO 8601 |
| `sharedWithGroups` | [[GroupWithPortalRoles](#groupwithportalroles)] | |
| `thumbnailsUrls` | [string] | Signed S3 URLs |
| `regardingInstitutionProfileId` | int\|null | |
| `currentUserCanEdit` | bool | |
| `currentUserCanDelete` | bool | |
| `currentUserCanAddMedia` | bool | |

---

### gallery.getMedia

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `albumId`, `index`, `limit`, `sortOn` ("uploadedAt"), `orderDirection`, `filterBy`, `filterInstProfileIds[]=<int>` |

**Response** `data`:

| Property | Type | Description |
|---|---|---|
| `album` | object | Same shape as getAlbums item |
| `mediaCount` | int | |
| `results` | array | Media items |
| `totalSize` | int | |
| `limit` | int | |
| `startIndex` | int | |

---

## Posts

### posts.getAllPosts

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `parent` ("profile"), `index`, `institutionProfileIds[]=<int>`, `limit` |

**Response** `data`:

| Property | Type | Description |
|---|---|---|
| `posts` | [Post] | |

`Post`:

| Property | Type | Description |
|---|---|---|
| `id` | int | |
| `title` | string | |
| `content` | object | `{ html: string }` |
| `timestamp` | string | ISO 8601 |
| `ownerProfile` | [InstitutionProfileBrief](#institutionprofilebrief) (with institution, gender, mailBoxId) | |
| `allowComments` | bool | |
| `sharedWithGroups` | [[GroupWithPortalRoles](#groupwithportalroles)] | |
| `publishAt` | string | ISO 8601 |
| `isPublished` | bool | |
| `expireAt` | string | ISO 8601 |
| `isExpired` | bool | |
| `isImportant` | bool | |
| `importantFrom` | string\|null | |
| `importantTo` | string\|null | |
| `relatedProfiles` | array | InstitutionProfile objects of related children |
| `attachments` | array | |
| `pendingMedia` | bool | |
| `commentCount` | int | |
| `canCurrentUserDelete` | bool | |
| `canCurrentUserReport` | bool | |
| `canCurrentUserComment` | bool | |
| `editedAt` | string\|null | |
| `isBookmarked` | bool | |

---

## Groups

### groups.getGroupsByContext

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `childInstitutionProfileIds[]=<int>` |

**Response** `data`: array of:

| Property | Type | Description |
|---|---|---|
| `groups` | array | `[{ id, name, showAsDefault, institutionCode }]` |
| `profileId` | int | |
| `displayName` | string | |

---

## Consents

### consents.getConsentResponses

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `returnOnlyPendingConsentResponses=<bool>` |

**Response** `data`: array of:

| Property | Type | Description |
|---|---|---|
| `institutionProfile` | [InstitutionProfileBrief](#institutionprofilebrief) (full variant with institution, gender, profilePicture, mainGroupName) | |
| `consentResponses` | [ConsentResponse] | |

`ConsentResponse`:

| Property | Type | Description |
|---|---|---|
| `id` | int | |
| `consentId` | int | |
| `consentDescription` | string | |
| `allowedAnswers` | [string] | e.g. ["class_or_stue", "institution", "not_at_all"] |
| `viewOnlyDependency` | any\|null | |
| `consentResponseAnswer` | string | e.g. "institution" |
| `consentResponseStatus` | string | "active" |
| `viewOrder` | int | |
| `editable` | bool | |

---

## Municipal Configuration

### municipalConfiguration.getBlockedCommunicationProfiles

| | |
|---|---|
| **HTTP** | `GET` |

**Response** `data`:

| Property | Type | Description |
|---|---|---|
| `child` | string | |
| `guardian` | string | |
| `employee` | string | |
| `isBlockedAllProfileTypes` | bool | |

---

### municipalConfiguration.getCalendarFeedEnabled

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `municipalityCodes[]=<string>` |

**Response** `data`: `[{ municipalityCode: string, calendarFeedEnabled: bool }]`

---

### municipalConfiguration.getSameAdministrativeAuthorityInstitutions

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `institutionCode=<string>` |

**Response** `data`: array of:

| Property | Type | Description |
|---|---|---|
| `institutionCode` | string | |
| `institutionName` | string | |
| `municipalityCode` | string | |
| `municipalityName` | string | |
| `type` | string | "School" / "Daycare" |
| `administrativeAuthority` | object | `{ id, name, institutionCodes }` |

---

## Calendar Feed

### CalendarFeed.getFeedConfigurations

| | |
|---|---|
| **HTTP** | `GET` |
| **Response** | `data: []` |

### CalendarFeed.getPolicyAnswer

| | |
|---|---|
| **HTTP** | `GET` |
| **Response** | `data: { policyAccepted: bool }` |

---

## Aula Tokens (Widgets)

### aulaToken.getAulaToken

Returns a JWT token for a specific widget.

| | |
|---|---|
| **HTTP** | `GET` |
| **Params** | `widgetId=<string>` |

**Response** `data`: `string` (JWT token)

Observed widget IDs: `0003`, `0004`, `0040`, `0047`, `0119`, `0147`

---

## Meebook APIs

### GET /rest/app-config

Returns user configuration, menus, feature flags, and settings.

| Property | Type | Description |
|---|---|---|
| `usertype` | string | "related" (guardian) |
| `userId` | int | Meebook user ID |
| `unilogin` | string | |
| `name` | string | |
| `locale` | string | "da" |
| `menus` | object | `{ top, main, none }` - menu structure |
| `featureFlags` | object | Feature toggle map |
| `sectionPermissions` | object | Content section permissions |
| `settings` | object | Instance settings |
| `globalOptions` | object | Global config options |
| `hasTwoFactor` | bool | |
| `wshost` | string | WebSocket host |
| `aiApiUrl` | string | AI API endpoint |

---

### GET /rest/related/students

Returns students related to the logged-in user.

**Response**: `{ items: [{ id: int, name: string }] }`

---

### GET /rest/weekplan/events

Returns weekly plan events (lessons, homework) for a student.

| | |
|---|---|
| **Params** | `studentId=<int>`, `startDate=<YYYY-MM-DD>`, `endDate=<YYYY-MM-DD>` |

**Response** `items`: array of:

| Property | Type | Description |
|---|---|---|
| `id` | string | Format: "eventId-studentId" |
| `sectionId` | int\|null | |
| `isVisible` | bool | |
| `categories` | [string] | Subject names, e.g. ["Dansk"], ["Matematik"] |
| `studentId` | int | |
| `annualPlanId` | int | |
| `type` | string | "comment" (class activity) or "task" (homework/lektie) |
| `text` | string | Description text |
| `date` | string | "YYYY-MM-DD" |

---

### GET /aulaapi/relatedweekplan/all (Aula Widget)

Returns formatted weekly plan for Aula widget display.

| | |
|---|---|
| **Params** | `currentWeekNumber` (ISO week, e.g. "2026-W12"), `userProfile`, `childFilter[]`, `institutionFilter[]` |

**Response**: array of:

| Property | Type | Description |
|---|---|---|
| `id` | int | Meebook student ID |
| `name` | string | |
| `unilogin` | string | |
| `weekPlan` | [WeekPlanDay] | |

`WeekPlanDay`:

| Property | Type | Description |
|---|---|---|
| `date` | string | Danish formatted, e.g. "mandag 16. mar." |
| `tasks` | [WeekPlanTask] | |

`WeekPlanTask`:

| Property | Type | Description |
|---|---|---|
| `id` | int | |
| `type` | string | "comment" / "task" |
| `group` | string | Group name, e.g. "1A" |
| `pill` | string | Subject name, e.g. "Dansk" |
| `content` | string | Task description |

---

### GET /aulaapi/relatedweeklybook/all (Aula Widget)

Returns weekly books/materials for Aula widget.

| | |
|---|---|
| **Params** | `currentWeekNumber`, `userProfile`, `childFilter[]`, `institutionFilter[]` |

**Response**: array of:

| Property | Type | Description |
|---|---|---|
| `id` | int | Student ID |
| `name` | string | |
| `unilogin` | string | |
| `books` | array | `[{ id: int, title: string, category: string }]` |

---

### GET /aulaapi/relatednotifications (Aula Widget)

Returns Meebook notifications for Aula widget.

| | |
|---|---|
| **Params** | `currentWeekNumber`, `userProfile`, `childFilter[]`, `institutionFilter[]` |

**Response**:

| Property | Type | Description |
|---|---|---|
| `links` | array | `[{ label, path }]` - navigation links |
| `notifications.items` | array | See below |
| `notifications.pagination` | object | `{ nextCursor: string|null }` |

`NotificationItem`:

| Property | Type | Description |
|---|---|---|
| `id` | int | |
| `date` | string | ISO 8601 |
| `type` | string | "annualplan_published" |
| `link` | string | Deep link path |
| `data` | object | `{ studentName, groupName, categories, yearSpan, isVisibleForRelated, senderId, senderType, senderName }` |

---

## Shared Types

### Address

| Property | Type | Description |
|---|---|---|
| `id` | int | |
| `street` | string | |
| `postalCode` | int | |
| `postalDistrict` | string | |

### ProfilePicture

| Property | Type | Description |
|---|---|---|
| `id` | int | |
| `key` | string | S3 key |
| `bucket` | string | "aula-prod-media" |
| `isImageScalingPending` | bool | |
| `url` | string | Signed URL with expiry |
| `scanningStatus` | string | "bypassed" |

### GroupBrief

| Property | Type | Description |
|---|---|---|
| `id` | int | |
| `name` | string | |
| `shortName` | string | |
| `institutionCode` | string | |
| `institutionName` | string | |
| `mainGroup` | bool | |
| `uniGroupType` | string | "Hovedgruppe" / "" |
| `isDeactivated` | bool | |
| `allowMembersToBeShown` | bool | |

### GroupDetailed

Same as GroupBrief.

### GroupWithPortalRoles

Extends GroupBrief with:

| Property | Type | Description |
|---|---|---|
| `portalRoles` | [string] | e.g. ["guardian"], ["employee", "guardian"] |

### InstitutionProfileBrief

| Property | Type | Description |
|---|---|---|
| `profileId` | int | |
| `id` | int | instProfileId |
| `institutionCode` | string | |
| `institutionName` | string | |
| `role` | string | "child" / "employee" / "guardian" |
| `name` | string | |
| `profilePicture` | [ProfilePicture](#profilepicture)\|null | |
| `mainGroup` | string\|null | |
| `shortName` | string | |
| `institutionRole` | string | "early-student", "daycare", "leader", "preschool-teacher", "guardian" |
| `metadata` | string | Context string |

### MessageSender

| Property | Type | Description |
|---|---|---|
| `shortName` | string | |
| `profilePicture` | object | `{ url: string }` |
| `institutionCode` | string | |
| `mailBoxOwner` | [MailBoxOwner](#mailboxowner) | |
| `fullName` | string | |
| `metadata` | string | |
| `answerDirectlyName` | string | |

### MailBoxOwner

| Property | Type | Description |
|---|---|---|
| `profileId` | int | |
| `portalRole` | string | "employee" / "guardian" |
| `isDeactivated` | bool | |
| `mailBoxOwnerType` | string | "institutionProfile" |
| `id` | int | instProfileId |

### Creator

| Property | Type | Description |
|---|---|---|
| `profileId` | int | |
| `id` | int | instProfileId |
| `institutionCode` | string | |
| `institutionName` | string | |
| `role` | string | |
| `name` | string | |
| `profilePicture` | [ProfilePicture](#profilepicture)\|null | |
| `mainGroup` | string\|null | |
| `shortName` | string | |
| `institutionRole` | string | |
| `metadata` | string | |

---

## External Widget APIs

### IBK Services (nordiccloud)

**GET** `https://aulawidgetapi.nordiccloud.dk/api/confidential/user/v2`
**GET** `https://aulawidgetapi.nordiccloud.dk/api/confidential/institution/v2`

Params: `userProfile`, `assuranceLevel`, `childFilter`

### IBK Services (ibkservices.dk)

**GET** `https://api.ibkservices.dk/?institutionsnummer=<codes>&userprofile=<role>`

Returns widget availability per institution.
